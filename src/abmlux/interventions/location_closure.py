"""Represents interventions to the system."""

import logging

from abmlux.interventions import Intervention
from abmlux.messagebus import MessageBus

log = logging.getLogger("location_closures")

class LocationClosures(Intervention):
    """Close a given set of locations.

    In response to a request to change location, this will consume the event and re-publish
    a request to change location to move home instead."""

    def __init__(self, prng, config, clock, bus, state):
        super().__init__(prng, config, clock, bus)

        self.location_closures  = config['location_closures']['locations']
        self.home_activity_type = state.activity_manager.as_int(\
            config['location_closures']['home_activity_type'])

        self.bus.subscribe("request.agent.location", self.handle_location_change, self)

    def handle_location_change(self, agent, new_location):
        """If the new location is in the blacklist, send the agent home."""

        if new_location.typ in self.location_closures:

            home_location = agent.locations_for_activity(self.home_activity_type)[0]
            if new_location != home_location:
                self.bus.publish("request.agent.location", agent, home_location)
                return MessageBus.CONSUME
