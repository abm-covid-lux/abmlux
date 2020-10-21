"""Simple location selection without bias for proximity."""

import logging

from abmlux.location_model import LocationModel
import abmlux.random_tools as rt
from abmlux.messagebus import MessageBus

log = logging.getLogger("simple_location_model")

class SimpleRandomLocationModel(LocationModel):
    """Uses simple random sampling to select locations in response to activity changes."""

    def __init__(self, prng, config, bus, activity_manager):

        # TODO: semantic constructor arguments rather than just passing in the whole config
        super().__init__(prng, config, bus, activity_manager)

        self.no_move_states = config['location_model']['no_move_health_states']

        self.bus.subscribe("request.agent.activity", self.handle_activity_change, self)


    def handle_activity_change(self, agent, new_activity):
        """Respond to an activity by sending location change requests."""

        # If agent is hospitalised or dead, don't change location in response to new activity
        if agent.health in self.no_move_states:
            return MessageBus.CONSUME

        # Change location in response to new activity
        allowable_locations = agent.locations_for_activity(new_activity)
        self.bus.publish("request.agent.location", agent, \
                         rt.random_choice(self.prng, list(allowable_locations)))
