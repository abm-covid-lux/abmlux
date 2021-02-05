"""Represents interventions to the system."""

import logging
import datetime

from abmlux.interventions import Intervention
from abmlux.messagebus import MessageBus

log = logging.getLogger("curfew")

# This file uses callbacks and interfaces which make this hit many false positives
#pylint: disable=unused-argument
#pylint: disable=attribute-defined-outside-init
class Curfew(Intervention):
    """Close a given set of locations during given hours.

    In response to a request to change location during these hours, this will consume the event and
    re-publish a request to change location to move home instead."""

    def __init__(self, config, init_enabled):
        super().__init__(config, init_enabled)

        self.active = False

        self.start_time = datetime.time(self.config['start_time'])
        self.end_time = datetime.time(self.config['end_time'])
        self.curfew_locations = self.config['locations']
        self.home_activity_type = None

    def init_sim(self, sim):
        super().init_sim(sim)

        self.home_activity_type = sim.activity_manager.as_int(self.config['home_activity_type'])

        self.bus.subscribe("notify.time.tick", self.handle_time_change, self)
        self.bus.subscribe("request.agent.location", self.handle_location_change, self)

    def handle_time_change(self, clock, t):
        """If the time moves within a certain interval, then enable the curfew, else disable"""

        current_time = clock.now()
        if current_time.time() >= self.start_time or current_time.time() < self.end_time:
            self.active = True
        else:
            self.active = False

    def handle_location_change(self, agent, new_location):
        """If the new location is in the blacklist, send the agent home."""

        # If disabled, don't intervene
        if not self.enabled:
            return

        if not self.active:
            return

        if new_location.typ in self.curfew_locations:
            home_location = agent.locations_for_activity(self.home_activity_type)[0]
            if new_location != home_location:
                self.bus.publish("request.agent.location", agent, home_location)
                return MessageBus.CONSUME
