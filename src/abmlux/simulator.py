"""Simulates an epidemic"""

import logging
from abmlux.version import VERSION
from datetime import datetime
import uuid
from collections import defaultdict
from random import Random
import time

from tqdm import tqdm

from abmlux.telemetry import TelemetryServer
from abmlux.scheduler import Scheduler
from abmlux.messagebus import MessageBus
from abmlux.agent import Agent
from abmlux.location import Location
from abmlux.disease_model import DiseaseModel
from abmlux.interventions import Intervention
from abmlux.world import World
from abmlux.activity_manager import ActivityManager
from abmlux.sim_time import SimClock

log = logging.getLogger('sim')

class Simulator:
    """Class that simulates an outbreak."""

    def __init__(self, config, activity_manager, clock, _map, \
                 world_model, activity_model, movement_model, \
                 disease_model, interventions, intervention_schedules):

        self.telemetry_server = TelemetryServer(config['telemetry.host'], config['telemetry.port'])

        # Static info
        self.abmlux_version = VERSION
        self.created_at     = datetime.now()
        self.run_id         = uuid.uuid4().hex

        log.info("Simulation created at %s with ID=%s", self.created_at, self.run_id)

        self.config                 = config
        self.activity_manager       = activity_manager
        self.clock                  = clock
        self.bus                    = MessageBus()

        # Components of the simulation
        self.map                    = _map
        self.world                  = world_model
        self.activity_model         = activity_model
        self.movement_model         = movement_model
        self.disease_model          = disease_model
        self.interventions          = interventions
        self.intervention_schedules = intervention_schedules

        # FIXME: remove the block below if possible
        self.locations     = self.world.locations
        self.agents        = self.world.agents

    def _initialise_components(self):
        """Tell components that a simulation is starting.

        This allows them to complete any final setup tasks on their internal state, and gives
        access to the simulation state as a whole to enable interactions between the components
        and the state of the world."""

        # Configure reporting
        self.activity_model.set_telemetry_server(self.telemetry_server)
        self.movement_model.set_telemetry_server(self.telemetry_server)
        self.disease_model.set_telemetry_server(self.telemetry_server)
        for name, intervention in self.interventions.items():
            intervention.set_telemetry_server(self.telemetry_server)

        # Here we assume that components are going to hook onto the messagebus.
        # We start with the activity model
        self.activity_model.init_sim(self)
        self.movement_model.init_sim(self)
        self.disease_model.init_sim(self)
        for name, intervention in self.interventions.items():
            log.info("Initialising intervention '%s'...", name)
            intervention.init_sim(self)

        # The sim is registered on the bus last, so they catch any events that have not been
        # inhibited by earlier processing stages.
        self.agent_updates = defaultdict(dict)
        self.bus.subscribe("request.agent.location", self.record_location_change, self)
        self.bus.subscribe("request.agent.activity", self.record_activity_change, self)
        self.bus.subscribe("request.agent.health", self.record_health_change, self)

        # For manipulating interventions
        self.scheduler = Scheduler(self.clock, self.intervention_schedules)

    def record_location_change(self, agent, new_location):
        """Record request.agent.location events, placing them on a queue to be enacted
        at the end of the tick."""

        self.agent_updates[agent]['location'] = new_location
        return MessageBus.CONSUME

    def record_activity_change(self, agent, new_activity):
        """Record request.agent.activity events, placing them on a queue to be enacted
        at the end of the tick.

        If the activity is changing, this may trigger a change in location, e.g. a change to a
        'home' activity will cause this function to emit a request to move the agent to its home.
        """

        self.agent_updates[agent]['activity'] = new_activity
        return MessageBus.CONSUME

    def record_health_change(self, agent, new_health):
        """Record request.agent.health events, placing them on a queue to be enacted
        at the end of the tick.

        Certain changes in health state will cause agents to request changes of location, e.g.
        to a hospital."""

        self.agent_updates[agent]['health'] = new_health
        return MessageBus.CONSUME

    def run(self):
        """Run the simulation"""

        log.info("Simulating outbreak...")
        log.info( "To get better output, connect to the telemetry endpoint "
                 f"(host={self.config['telemetry.host']}, port={self.config['telemetry.port']})")

        # Initialize interventions here?
        self.clock.reset()
        current_day = self.clock.now().day

        self._initialise_components()

        self.bus.publish("notify.time.start_simulation", self)

        # Allow the reporter threads time to start
        time.sleep(10)

        self.telemetry_server.send("simulation.start", self.world.scale_factor)

        # Send telemetry server agent ids to use when recording secondary infection counts
        agent_uuids = []
        for agent in self.agents:
            agent_uuids.append(agent.uuid)
        self.telemetry_server.send("agent_uuids", agent_uuids)

        # Send initial distribution of agents across location types to telemetry server
        location_type_counts_initial = {str(lt): 0 for lt in self.movement_model.location_types}
        for agent in self.agents:
            location_type_counts_initial[str(agent.current_location.typ)] += 1
        self.telemetry_server.send("location_type_counts.initial", self.run_id, self.created_at, location_type_counts_initial)

        # Send initial distribution of agents across activities to telemetry server
        activity_counts_initial = {str(self.activity_manager.as_str(at)): 0 for at in list(self.activity_manager.map_config.keys())}
        for agent in self.agents:
            activity_counts_initial[str(self.activity_manager.as_str(agent.current_activity))] += 1
        self.telemetry_server.send("activity_counts.initial", self.run_id, self.created_at, activity_counts_initial)

        # Send initial distribution of agents across health states to telemetry server
        health_state_counts_initial = {str(hs): 0 for hs in self.disease_model.states}
        for agent in self.agents:
            health_state_counts_initial[str(agent.health)] += 1
        self.telemetry_server.send("health_state_counts.initial", self.run_id, self.created_at, health_state_counts_initial)

        # Simulation state.  These indices represent an optimisation to prevent having to loop
        # over every single agent.
        log.info("Creating agent location indices...")
        self.attendees = {l: {h: set() for h in self.disease_model.states} for l in self.locations}
        for a in tqdm(self.agents):
            self.attendees[a.current_location][a.health].add(a)

        update_notifications = []
        for t in self.clock:
            self.telemetry_server.send("world.time", self.clock)

            # Enable/disable interventions
            self.scheduler.tick(t)

            # Send out notifications of what has changed since last tick
            for topic, *params in update_notifications:
                self.bus.publish(topic, *params)

            # Send tick event --- things respond to this with intents
            self.bus.publish("notify.time.tick", self.clock, t)
            if current_day != self.clock.now().day:
                current_day = self.clock.now().day
                self.bus.publish("notify.time.midnight", self.clock, t)
                self.telemetry_server.send("notify.time.midnight", self.clock, t)

            # - 3 - Actually enact changes in an atomic manner
            update_notifications = self._update_agents()

        self.telemetry_server.send("simulation.end")
        self.bus.publish("notify.time.end_simulation", self)

    def _update_agents(self):
        """Update the state of agents according to the lists provided."""

        update_notifications = []
        telemetry_notifications = []

        for agent, updates in self.agent_updates.items():

            # -------------------------------------------------------------------------------------

            if 'activity' in updates:

                old_activity = agent.current_activity
                agent.set_activity(updates['activity'])
                update_notifications.append(("notify.agent.activity", agent, old_activity))
                telemetry_notifications.append(("activity_counts.update", str(self.activity_manager.as_str(agent.current_activity)), str(self.activity_manager.as_str(old_activity))))

            # -------------------------------------------------------------------------------------
            
            if 'health' in updates or 'location' in updates:

                self.attendees[agent.current_location][agent.health].remove(agent)

                # ---------------------------------------------------------------------------------

                if 'health' in updates:

                    old_health = agent.health
                    agent.health = updates['health']
                    update_notifications.append(("notify.agent.health", agent, old_health))
                    telemetry_notifications.append(("health_state_counts.update", str(agent.health), str(old_health)))

                if 'location' in updates:

                    old_location = agent.current_location
                    agent.set_location(updates['location'])
                    update_notifications.append(("notify.agent.location", agent, old_location))
                    telemetry_notifications.append(("location_type_counts.update", str(agent.current_location.typ), str(old_location.typ)))

                # ---------------------------------------------------------------------------------

                self.attendees[agent.current_location][agent.health].add(agent)

        self.agent_updates = defaultdict(dict)
        self.telemetry_server.send("world.updates", self.clock, telemetry_notifications)
        return update_notifications
