"""Simple location selection without bias for proximity."""

import logging

from abmlux.movement_model import MovementModel
from abmlux.messagebus import MessageBus

log = logging.getLogger("simple_movement_model")

class SimpleRandomMovementModel(MovementModel):
    """Uses simple random sampling to select locations in response to activity changes."""

    def init_sim(self, sim):
        super().init_sim(sim)

        self.no_move_states = self.config['no_move_health_states']
        self.bus.subscribe("request.agent.activity", self.handle_activity_change, self)


    def handle_activity_change(self, agent, new_activity):
        """Respond to an activity by sending location change requests."""

        # If agent is hospitalised or dead, don't change location in response to new activity
        if agent.health in self.no_move_states:
            return MessageBus.CONSUME

        # Change location in response to new activity
        allowable_locations = agent.locations_for_activity(new_activity)
        self.bus.publish("request.agent.location", agent, \
                         self.prng.random_choice(list(allowable_locations)))
