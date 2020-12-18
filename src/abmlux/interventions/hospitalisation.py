"""Respond to health states by moving agents"""

import logging

from abmlux.interventions import Intervention

log = logging.getLogger("hospitalisation")

# This file uses callbacks and interfaces which make this hit many false positives
#pylint: disable=unused-argument
#pylint: disable=attribute-defined-outside-init
class Hospitalisation(Intervention):
    """Hospitalise agents who are in certain health states, and move agents in certain health
    states into cemeteries."""

    def init_sim(self, sim):

        super().init_sim(sim)

        self.dead_states            = self.config['dead_states']
        self.hospital_states        = self.config['hospital_states']
        self.cemetery_location_type = self.config['cemetery_location_type']
        self.hospital_location_type = self.config['hospital_location_type']

        # Overridden later when the simulation states
        self.cemeteries = []
        self.hospitals  = []

        self.cemeteries = sim.world.locations_by_type[self.cemetery_location_type]
        self.hospitals  = sim.world.locations_by_type[self.hospital_location_type]

        # Respond to requested location changes by moving people home
        self.bus.subscribe("notify.agent.health", self.handle_health_change, self)

    def handle_health_change(self, agent, new_health):
        """Respond to a change in health status by moving the agent to a hospital.

        Respond to a change in health status by moving the agent to a cemetery.
        """

        # If we are disabled, don't tell people to go to hospital.
        if not self.enabled:
            return

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
                                 self.prng.random_choice(self.hospitals))

        if agent.health in self.dead_states:
            if agent.current_location not in self.cemeteries:
                self.bus.publish("request.agent.location", agent, \
                                 self.prng.random_choice(self.cemeteries))
