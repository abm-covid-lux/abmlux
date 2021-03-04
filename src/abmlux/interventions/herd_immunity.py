"""Represents herd immunity"""

import logging

from abmlux.interventions import Intervention

log = logging.getLogger("herd_immunity")

# This file uses callbacks and interfaces which make this hit many false positives
#pylint: disable=unused-argument
#pylint: disable=attribute-defined-outside-init
class HerdImmunity(Intervention):
    """Confer a proportion of the population with total immunity"""

    def __init__(self, config, init_enabled):
        super().__init__(config, init_enabled)

    def init_sim(self, sim):
        super().init_sim(sim)

        self.proportion_immune = self.config['proportion_immune']

        for agent in sim.world.agents:
            agent.vaccinated = self.prng.boolean(self.proportion_immune)
