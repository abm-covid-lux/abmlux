"""Simulates an epidemic"""

import logging

from datetime import datetime
import uuid
from collections import defaultdict
from tqdm import tqdm

from abmlux.version import VERSION
from abmlux.scheduler import Scheduler
from abmlux.messagebus import MessageBus

log = logging.getLogger('sim')

#pylint: disable=unused-argument
#pylint: disable=attribute-defined-outside-init
class Simulator:
    """Class that simulates an outbreak."""

    def __init__(self, config, activity_manager, clock, _map, \
                 world_model, activity_model, movement_model, \
                 disease_model, interventions, intervention_schedules, \
                 telemetry_bus):

        self.telemetry_bus = telemetry_bus

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
        self.activity_model.set_telemetry_bus(self.telemetry_bus)
        self.movement_model.set_telemetry_bus(self.telemetry_bus)
        self.disease_model.set_telemetry_bus(self.telemetry_bus)
        for name, intervention in self.interventions.items():
            intervention.set_telemetry_bus(self.telemetry_bus)

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

        # Set the correct time
        self.clock.reset()
        current_day = self.clock.now().day

        # Initialise components, such as disease model, movement model, interventions etc
        self._initialise_components()
        #self.telemetry_bus.publish("simulation.start", self.run_id, self.created_at, \
        #                           self.clock, self.world, self.disease_model.states)

        # Notify message bus of simulation start
        self.bus.publish("notify.time.start_simulation", self)

        # List of location types, activites and health states
        self.location_types = self.movement_model.location_types
        self.activities     = list(self.activity_manager.map_config.keys())
        self.health_states  = self.disease_model.states

        # Partition attendees according to health and activity, respectively, for optimization
        log.info("Creating agent location indices...")
        self.attendees_by_health   = {l: {h: [] for h in self.disease_model.states}
                                      for l in self.locations}
        self.attendees_by_activity = {l: {self.activity_manager.as_int(act): [] for act in
                                      self.activities} for l in self.locations}
        for agent in tqdm(self.agents):
            location = agent.current_location
            activity = agent.current_activity
            health = agent.health
            self.attendees_by_health[location][health].append(agent)
            self.attendees_by_activity[location][activity].append(agent)

        # Notify telemetry server of simulation start, send agent ids and initial counts
        self.telemetry_bus.publish("simulation.start")
        agent_uuids = [agent.uuid for agent in self.agents]
        self.telemetry_bus.publish("agent_data.initial", agent_uuids)
        self.agents_by_location_type_counts = {lt: sum([sum([len(att) for att in
            self.attendees_by_health[loc].values()]) for loc in self.locations if loc.typ == lt])
            for lt in self.location_types}
        self.telemetry_bus.publish("agents_by_location_type_counts.initial",
            self.agents_by_location_type_counts)
        self.agents_by_activity_counts = {act:
            sum([len(self.attendees_by_activity[loc][self.activity_manager.as_int(act)]) for
            loc in self.locations]) for act in self.activities}
        self.telemetry_bus.publish("agents_by_activity_counts.initial",
            self.agents_by_activity_counts)
        self.region = self.config['region']
        self.resident_agents_by_health_state_counts = {hs: sum([len({a for a in
            self.attendees_by_health[loc][hs] if a.nationality == self.region}) for loc in
            self.locations]) for hs in self.health_states}
        self.telemetry_bus.publish("resident_agents_by_health_state_counts.initial",
            self.resident_agents_by_health_state_counts)

        # Start the main loop
        update_notifications = []
        for t in self.clock:
            self.telemetry_bus.publish("world.time", self.clock)
            # Enable/disable or update interventions
            self.scheduler.tick(t)

            # Notify the message bus of update notifications occuring since the last tick
            for topic, *params in update_notifications:
                self.bus.publish(topic, *params)

            # Notify the message bus and telemetry server of the current time
            self.bus.publish("notify.time.tick", self.clock, t)

            # If a new day has started, notify the message bus and telemetry server
            if current_day != self.clock.now().day:
                current_day = self.clock.now().day
                self.bus.publish("notify.time.midnight", self.clock, t)
                self.telemetry_bus.publish("notify.time.midnight", self.clock)

            # Actually enact changes in an atomic manner
            update_notifications = self._update_agents()

        # Notify the message bus and telemetry bus that the simulation has ended
        self.telemetry_bus.publish("simulation.end")
        self.bus.publish("notify.time.end_simulation", self)

    def _update_agents(self):
        """Update the state of agents according to the lists provided."""

        update_notifications = []

        for agent, updates in self.agent_updates.items():

            self.agents_by_location_type_counts[agent.current_location.typ] -= 1
            self.agents_by_activity_counts[self.activity_manager.as_str(agent.current_activity)]-= 1
            if agent.nationality == self.region:
                self.resident_agents_by_health_state_counts[agent.health] -= 1

            self.attendees_by_health[agent.current_location][agent.health].remove(agent)
            self.attendees_by_activity[agent.current_location][agent.current_activity].remove(agent)

            # -------------------------------------------------------------------------------------

            if 'activity' in updates:

                old_activity = agent.current_activity
                agent.set_activity(updates['activity'])
                update_notifications.append(("notify.agent.activity", agent, old_activity))

            if 'health' in updates:

                old_health = agent.health
                agent.set_health(updates['health'])
                update_notifications.append(("notify.agent.health", agent, old_health))

            if 'location' in updates:

                old_location = agent.current_location
                agent.set_location(updates['location'])
                update_notifications.append(("notify.agent.location", agent, old_location))

            # ---------------------------------------------------------------------------------

            self.agents_by_location_type_counts[agent.current_location.typ] += 1
            self.agents_by_activity_counts[self.activity_manager.as_str(agent.current_activity)]+= 1
            if agent.nationality == self.region:
                self.resident_agents_by_health_state_counts[agent.health] += 1

            self.attendees_by_health[agent.current_location][agent.health].append(agent)
            self.attendees_by_activity[agent.current_location][agent.current_activity].append(agent)

        self.telemetry_bus.publish("agents_by_location_type_counts.update", self.clock,
                                   self.agents_by_location_type_counts)
        self.telemetry_bus.publish("agents_by_activity_counts.update", self.clock,
                                   self.agents_by_activity_counts)
        self.telemetry_bus.publish("resident_agents_by_health_state_counts.update", self.clock,
                                   self.resident_agents_by_health_state_counts)

        self.agent_updates = defaultdict(dict)

        return update_notifications
