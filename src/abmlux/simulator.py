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

        # Set the correct time
        self.clock.reset()
        current_day = self.clock.now().day

        # Initialise components, such as disease model, movement model, interventions etc
        self._initialise_components()

        # Notify message bus of simulation start
        self.bus.publish("notify.time.start_simulation", self)

        # Allow the reporter threads time to start
        time.sleep(10)

        # List of location types, activites and health states
        self.location_types = self.movement_model.location_types
        self.activities     = list(self.activity_manager.map_config.keys())
        self.health_states  = self.disease_model.states

        # Partition attendees according to health and activity, respectively, for optimization
        log.info("Creating agent location indices...")
        self.attendees_by_health   = {l: {h: set() for h in self.disease_model.states} for l in self.locations}
        self.attendees_by_activity = {l: {self.activity_manager.as_int(act): set() for act in self.activities} for l in self.locations}
        for a in tqdm(self.agents):
            self.attendees_by_health[a.current_location][a.health].add(a)
            self.attendees_by_activity[a.current_location][a.current_activity].add(a)

        # Notify telemetry server of simulation start, send agent ids and initial counts
        self.telemetry_server.send("simulation.start")

        # ------------------------------------------------------------------------------------------

        home_activity_type = self.activity_manager.as_int("House") # TODO: remove string

        # Extract a list of age types (this is for telemetry)
        age_types_set = set()
        for agent in self.agents:
            age_types_set.add(agent.agetyp)
        age_types = list(age_types_set)

        # Extract a dictionary of where each agent lives (this is for telemetry)
        home_locations = {}
        for agent in self.agents:
            home_location = agent.locations_for_activity(home_activity_type)[0]
            home_locations[agent] = home_location

        # Determine household composition (this is for telemetry)
        profiles_by_home = {home: {at: 0 for at in age_types} for home in list(home_locations.values())}
        for agent in self.agents:
            profiles_by_home[home_locations[agent]][agent.agetyp] += 1
        
        # Associate a household composition to each agent (this is for telemetry)
        profiles_by_agent = {}
        for agent in self.agents:
            profiles_by_agent[agent.uuid] = profiles_by_home[home_locations[agent]]

        # List of agent ids (this is for telemetry)
        agent_uuids = [agent.uuid for agent in self.agents]

        # Send data to telemetry server
        self.telemetry_server.send("agent_data.initial", age_types, agent_uuids, profiles_by_agent)

        # ------------------------------------------------------------------------------------------

        self.agents_by_location_type_counts = {lt: sum([len(set().union(*self.attendees_by_health[loc].values())) for loc in self.locations if loc.typ == lt]) for lt in self.location_types}
        self.telemetry_server.send("agents_by_location_type_counts.initial", self.agents_by_location_type_counts)
        self.agents_by_activity_counts      = {act: sum([len(self.attendees_by_activity[loc][self.activity_manager.as_int(act)]) for loc in self.locations]) for act in self.activities}
        self.telemetry_server.send("agents_by_activity_counts.initial", self.agents_by_activity_counts)
        self.agents_by_health_state_counts  = {hs: sum([len(self.attendees_by_health[loc][hs]) for loc in self.locations]) for hs in self.health_states}
        self.telemetry_server.send("agents_by_health_state_counts.initial", self.agents_by_health_state_counts)

        # Start the main loop
        update_notifications = []
        for t in self.clock:

            # Enable/disable or update interventions
            self.scheduler.tick(t)

            # Notify the message bus of update notifications occuring since the last tick
            for topic, *params in update_notifications:
                self.bus.publish(topic, *params)

            # Notify the message bus and telemetry server of the current time
            self.bus.publish("notify.time.tick", self.clock, t)
            self.telemetry_server.send("world.time", self.clock)

            # If a new day has started, notify the message bus and telemetry server
            if current_day != self.clock.now().day:
                current_day = self.clock.now().day
                self.bus.publish("notify.time.midnight", self.clock, t)
                self.telemetry_server.send("notify.time.midnight", self.clock)

            # Actually enact changes in an atomic manner
            update_notifications = self._update_agents()

        # Notify the message bus and telemetry server that the simulation has ended
        self.bus.publish("notify.time.end_simulation", self)
        self.telemetry_server.send("simulation.end")

    def _update_agents(self):
        """Update the state of agents according to the lists provided."""

        update_notifications = []

        for agent, updates in self.agent_updates.items():

            self.agents_by_location_type_counts[agent.current_location.typ]                      -= 1
            self.agents_by_activity_counts[self.activity_manager.as_str(agent.current_activity)] -= 1
            self.agents_by_health_state_counts[agent.health]                                     -= 1

            self.attendees_by_health[agent.current_location][agent.health].remove(agent)
            self.attendees_by_activity[agent.current_location][agent.current_activity].remove(agent)

            # -------------------------------------------------------------------------------------

            if 'activity' in updates:

                old_activity = agent.current_activity
                agent.set_activity(updates['activity'])
                update_notifications.append(("notify.agent.activity", agent, old_activity))

            if 'health' in updates:

                old_health = agent.health
                agent.health = updates['health']
                update_notifications.append(("notify.agent.health", agent, old_health))

            if 'location' in updates:

                old_location = agent.current_location
                agent.set_location(updates['location'])
                update_notifications.append(("notify.agent.location", agent, old_location))

            # ---------------------------------------------------------------------------------

            self.agents_by_location_type_counts[agent.current_location.typ]                      += 1
            self.agents_by_activity_counts[self.activity_manager.as_str(agent.current_activity)] += 1
            self.agents_by_health_state_counts[agent.health]                                     += 1

            self.attendees_by_health[agent.current_location][agent.health].add(agent)
            self.attendees_by_activity[agent.current_location][agent.current_activity].add(agent)

        self.telemetry_server.send("agents_by_location_type_counts.update", self.clock, self.agents_by_location_type_counts)
        self.telemetry_server.send("agents_by_activity_counts.update", self.clock, self.agents_by_activity_counts)
        self.telemetry_server.send("agents_by_health_state_counts.update", self.clock, self.agents_by_health_state_counts)

        self.agent_updates = defaultdict(dict)

        return update_notifications
