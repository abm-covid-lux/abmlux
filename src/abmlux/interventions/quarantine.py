"""Represents the intervention of quarantining."""

import math
import logging
from tqdm import tqdm
from collections import deque, defaultdict

from abmlux.sim_time import DeferredEventPool
import abmlux.random_tools as random_tools
from abmlux.interventions import Intervention

log = logging.getLogger("quarantine")

class Quarantine(Intervention):

    def __init__(self, prng, config, clock, bus, state):
        super().__init__(prng, config, clock, bus)

        self.default_duration_days  = int(self.clock.days_to_ticks(config['quarantine']['default_duration_days']))
        self.early_end_days         = int(self.clock.days_to_ticks(config['quarantine']['negative_test_result_to_end_quarantine_days']))
        self.location_blacklist     = config['quarantine']['location_blacklist']
        self.home_activity_type     = state.activity_manager.as_int(config['quarantine']['home_activity_type'])

        self.end_quarantine_events = DeferredEventPool(bus, self.clock)
        self.agents_in_quarantine  = set()

        self.bus.subscribe("testing.result", self.handle_test_result)
        self.bus.subscribe("quarantine.start", self.handle_start_quarantine)
        self.bus.subscribe("agent.location.change", self.handle_location_change)
        self.bus.subscribe("quarantine.end", self.handle_end_quarantine)

    def handle_test_result(self, agent, result):
        """Respond to positive test results by starting quarantine.
        Respond to negative test results by ending quarantine."""

        if agent in self.agents_in_quarantine and result == False:
            self.end_quarantine_events.add("quarantine.end", self.early_end_days, agent)

        elif agent not in self.agents_in_quarantine and result == True:
            self.agents_in_quarantine.add(agent)
            self.end_quarantine_events.add("quarantine.end", self.default_duration_days, agent)

    def handle_start_quarantine(self, agent):
        """Immediate start quarantine, unless the agent is already in quarantine"""

        if agent in self.agents_in_quarantine:
            return

        self.agents_in_quarantine.add(agent)
        self.end_quarantine_events.add("quarantine.end", self.default_duration_days, agent)

    def handle_location_change(self, agent, new_location):
        """Catch any location changes that will move quarantined agents out of their home,
        and rebroadcast an event to move them home again."""

        if agent in self.agents_in_quarantine:
            home_location = agent.locations_for_activity(self.home_activity_type)[0]
            if new_location.typ != home_location.typ:
                if new_location.typ not in self.location_blacklist:
                    self.bus.publish("agent.location.change", agent, home_location)

    def handle_end_quarantine(self, agent):
        """Ends quarantine."""

        if agent in self.agents_in_quarantine:
            self.agents_in_quarantine.remove(agent)