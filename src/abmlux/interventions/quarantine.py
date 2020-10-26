"""Represents the intervention of quarantining."""

import logging

from abmlux.sim_time import DeferredEventPool
from abmlux.interventions import Intervention
from abmlux.messagebus import MessageBus

log = logging.getLogger("quarantine")

# This file uses callbacks and interfaces which make this hit many false positives
#pylint: disable=unused-argument
class Quarantine(Intervention):
    """Intervention that applies quarantine rules.

    Agents are forced to return to certain locations when they request to move."""

    def __init__(self, prng, config, clock, bus, state, init_enabled):
        super().__init__(prng, config, clock, bus, init_enabled)

        self.default_duration_days  = int(self.clock.days_to_ticks(config['default_duration_days']))
        self.early_end_days         = int(self.clock.days_to_ticks(config['negative_test_result_to_end_quarantine_days']))
        self.location_blacklist     = config['location_blacklist']
        self.home_activity_type     = state.activity_manager.as_int(config['home_activity_type'])
        self.disable_releases_immediately = config['disable_releases_immediately']

        self.end_quarantine_events = DeferredEventPool(bus, self.clock)
        self.agents_in_quarantine  = set()

        # What to do this tick
        self.agents_to_add    = set()
        self.agents_to_remove = set()

        # Enter/leave quarantine
        self.bus.subscribe("notify.time.tick", self.update_quarantine_status, self)
        # Queue people up to enter/leave quarantine this tick
        self.bus.subscribe("notify.testing.result", self.handle_test_result, self)
        self.bus.subscribe("request.quarantine.start", self.handle_start_quarantine, self)
        self.bus.subscribe("request.quarantine.stop", self.handle_end_quarantine, self)
        # Respond to requested location changes by moving people home
        self.bus.subscribe("request.agent.location", self.handle_location_change, self)

    def update_quarantine_status(self, clock, t):
        """Take lists of things to do and apply them."""
        for agent in self.agents_to_add:
            if agent not in self.agents_in_quarantine:
                self.agents_in_quarantine.add(agent)
                self.end_quarantine_events.add("request.quarantine.stop", \
                                               self.default_duration_days, agent)
                self.bus.publish("notify.quarantine.start", agent)
        self.agents_to_add = set()

        for agent in self.agents_to_remove:
            if agent in self.agents_in_quarantine:
                self.agents_in_quarantine.remove(agent)
                self.bus.publish("notify.quarantine.end", agent)
        self.agents_to_remove = set()

    def handle_test_result(self, agent, result):
        """Respond to positive test results by starting quarantine.
        Respond to negative test results by ending quarantine."""

        if agent in self.agents_in_quarantine and not result:
            self.end_quarantine_events.add("request.quarantine.stop", self.early_end_days, agent)

        elif agent not in self.agents_in_quarantine and result:
            self.agents_in_quarantine.add(agent)
            self.end_quarantine_events.add("request.quarantine.stop", self.default_duration_days, agent)

    def handle_start_quarantine(self, agent):
        """Queues up agents to start quarantine next time quarantine status is updated."""

        # If intervention is disabled, don't ever put people in quarantine
        if not self.enabled:
            return

        if agent in self.agents_in_quarantine or agent in self.agents_to_add:
            return

        self.agents_to_add.add(agent)
        return MessageBus.CONSUME

    def handle_end_quarantine(self, agent):
        """Queues up agents to end quarantine next time quarantine status is updated."""

        if agent in self.agents_in_quarantine and agent not in self.agents_to_remove:
            self.agents_to_remove.add(agent)
        return MessageBus.CONSUME

    def handle_location_change(self, agent, new_location):
        """Catch any location changes that will move quarantined agents out of their home,
        and rebroadcast an event to move them home again.
        """

        # If we've been told to curtail all quarantines, allow people out.
        # They retain their quarantined status, so will be restricted again if quarantine
        # re-enables, but for now they're good.
        if self.disable_releases_immediately and not self.enabled:
            return

        if agent in self.agents_in_quarantine:
            home_location = agent.locations_for_activity(self.home_activity_type)[0]
            if new_location != home_location:
                if new_location.typ not in self.location_blacklist:
                    self.bus.publish("request.agent.location", agent, home_location)
                    return MessageBus.CONSUME
