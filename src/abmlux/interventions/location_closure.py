"""Represents interventions to the system."""

import logging

from abmlux.interventions import Intervention
from abmlux.messagebus import MessageBus

log = logging.getLogger("location_closures")

# This file uses callbacks and interfaces which make this hit many false positives
#pylint: disable=unused-argument
#pylint: disable=attribute-defined-outside-init
class LocationClosures(Intervention):
    """Close a given set of locations.

    In response to a request to change location, this will consume the event and re-publish
    a request to change location to move home instead."""

    def __init__(self, config, init_enabled):
        super().__init__(config, init_enabled)

        self.location_closures  = config['locations']

    def init_sim(self, sim):
        super().init_sim(sim)

        self.home_activity_type = sim.activity_manager.as_int(self.config['home_activity_type'])
        self.bus.subscribe("request.agent.location", self.handle_location_change, self)

    def handle_location_change(self, agent, new_location):
        """If the new location is in the blacklist, send the agent home."""

        # If disabled, don't intervene
        if not self.enabled:
            return

        if new_location.typ in self.location_closures:

            home_location = agent.locations_for_activity(self.home_activity_type)[0]
            if new_location != home_location:
                self.bus.publish("request.agent.location", agent, home_location)
                return MessageBus.CONSUME
