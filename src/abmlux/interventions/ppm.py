"""Represents the intervention of personal protective measures such as face masks."""

import logging

import abmlux.random_tools as random_tools
from abmlux.interventions import Intervention

log = logging.getLogger("ppm")

class PersonalProtectiveMeasures(Intervention):

    def __init__(self, prng, config, clock, bus, state):
        super().__init__(prng, config, clock, bus)

        self.incubating_states = set(config['incubating_states'])
        self.ppm_coeff = config['personal_protective_measures']['ppm_coeff']

        self.bus.subscribe("agent.health.change", self.handle_health_change)


    def handle_health_change(self, agent, new_health):
        """With a given probability: respond to a request to change health state by reversing it."""

        if new_health in self.incubating_states:
            if random_tools.boolean(self.prng, 1 - self.ppm_coeff):
                # Reverse transition
                self.bus.publish("agent.health.change", agent, agent.health)
