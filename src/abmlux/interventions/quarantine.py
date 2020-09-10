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
        self.bus.subscribe("quarantine", self.handle_quarantine_request)
        self.bus.subscribe("agent.location.change", self.handle_location_change)
        self.bus.subscribe("quarantine.end", self.handle_end_quarantine)

    def handle_test_result(self, agent, result):

        if agent in self.agents_in_quarantine:
            return

        if result == True:
            self.agents_in_quarantine.add(agent)
            self.end_quarantine_events.add("quarantine.end", self.default_duration_days, agent)

    def handle_quarantine_request(self, agent):

        if agent in self.agents_in_quarantine:
            return

        self.agents_in_quarantine.add(agent)
        self.end_quarantine_events.add(agent, lifespan=self.default_duration_days)

    def handle_location_change(self, agent, new_location):
        if agent in self.agents_in_quarantine:

            home_location = agent.locations_for_activity(self.home_activity_type)[0]
            if new_location.typ != home_location.typ:
                self.bus.publish("agent.location.change", agent, home_location)

    def handle_end_quarantine(self, agent):
        self.agents_in_quarantine.remove(agent)