"""Respond to health states by moving agents"""

import logging

from abmlux.interventions import Intervention
import abmlux.random_tools as rt

log = logging.getLogger("hospitalisation")

class Hospitalisation(Intervention):
    """Hospitalise agents who are in certain health states, and move agents in certain health
    states into cemeteries."""

    def __init__(self, prng, config, clock, bus, state):
        super().__init__(prng, config, clock, bus)

        self.dead_states            = config['dead_states']
        self.hospital_states        = config['hospital_states']
        self.cemetery_location_type = config['cemetery_location_type']
        self.hospital_location_type = config['hospital_location_type']

        # Overridden later when the simulation states
        self.cemeteries = []
        self.hospitals  = []

        # Respond to requested location changes by moving people home
        self.bus.subscribe("notify.agent.health", self.handle_health_change, self)
        self.bus.subscribe("notify.time.start_simulation", self.start_simulation, self)


    def start_simulation(self, sim):
        """New simulation.  Record the hospitals and cemeteries in this network for later use."""

        self.cemeteries      = sim.network.locations_by_type[self.cemetery_location_type]
        self.hospitals       = sim.network.locations_by_type[self.hospital_location_type]


    def handle_health_change(self, agent, new_health):
        """Respond to a change in health status by moving the agent to a hospital.

        Respond to a change in health status by moving the agent to a cemetery.
        """

        # If at time t the function get_health_transitions outputs 'HOSPITALIZING' for an agent,
        # then the function _get_activity_transitions will move that agent to hospital at the
        # first time, greater than or equal to t+1, at which the agent chooses to perform a new
        # activity. In other words, agents will finish the current activity before moving to
        # hospital, and similarly as regards leaving hospital. This simple implementation could
        # be modified by allowing activity_changes at time t to depend on health_changes at time
        # t and moreover by allowing agents to enter and exit hospital independently of their
        # Markov chain.
        if new_health in self.hospital_states:
            if agent.current_location not in self.hospitals:
                self.bus.publish("request.agent.location", agent, \
                                 rt.random_choice(self.prng, self.hospitals))

        elif agent.health in self.dead_states:
            if agent.current_location not in self.cemeteries:
                self.bus.publish("request.agent.location", agent, \
                                 rt.random_choice(self.prng, self.cemeteries))
