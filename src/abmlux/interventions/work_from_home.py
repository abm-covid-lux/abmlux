"""Represents interventions to the system."""

import logging

from abmlux.interventions import Intervention
from abmlux.messagebus import MessageBus
import abmlux.random_tools as random_tools

log = logging.getLogger("work_from_home")

# This file uses callbacks and interfaces which make this hit many false positives
#pylint: disable=unused-argument
class WorkFromHome(Intervention):
    """With a certain probability, force people to work from home.

    In response to a request to change location, with a certain probability, this will consume the
    event and re-publish a request to change location to move home instead."""

    def __init__(self, prng, config, clock, bus, state, init_enabled):
        super().__init__(prng, config, clock, bus, init_enabled)

        self.home_activity_type  = state.activity_manager.as_int(config['home_activity_type'])
        self.work_activity_type  = state.activity_manager.as_int(config['work_activity_type'])
        self.prob_work_from_home = config['prob_work_from_home']
        self.locations_exempt    = config['locations_exempt']

        self.bus.subscribe("request.agent.location", self.handle_location_change, self)

    def handle_location_change(self, agent, new_location):
        """If the new location is in the blacklist, send the agent home."""

        # If disabled, don't intervene
        if not self.enabled:
            return

        work_location = agent.locations_for_activity(self.home_activity_type)[0]
        if work_location.typ not in self.locations_exempt:
            if random_tools.boolean(self.prng, self.prob_work_from_home):
                home_location = agent.locations_for_activity(self.home_activity_type)[0]
                self.bus.publish("request.agent.location", agent, home_location)
                return MessageBus.CONSUME
