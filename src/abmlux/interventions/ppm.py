"""Represents the intervention of personal protective measures such as face masks."""

import logging

from abmlux.interventions import Intervention
from abmlux.messagebus import MessageBus

log = logging.getLogger("ppm")

# This file uses callbacks and interfaces which make this hit many false positives
#pylint: disable=unused-argument
#pylint: disable=attribute-defined-outside-init
class PersonalProtectiveMeasures(Intervention):
    """Models the use of personal protective measures by preventing propagation
    of health change events with a given probability."""

    def __init__(self, config, init_enabled):
        super().__init__(config, init_enabled)

        self.incubating_states = set(config['incubating_states'])
        self.ppm_coeff         = config['ppm_coeff']

    def init_sim(self, sim):
        super().init_sim(sim)

        self.bus.subscribe("request.agent.health", self.handle_health_change, self)

    def handle_health_change(self, agent, new_health):
        """With a given probability: respond to a request to change health state by censoring it."""

        # Respond to intervention enable/disable logic
        if self.enabled:
            if new_health in self.incubating_states:
                if self.prng.boolean(1 - self.ppm_coeff):

                    # Consume the event to prevent anything else responding
                    return MessageBus.CONSUME
