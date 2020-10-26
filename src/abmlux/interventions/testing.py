"""Represents large scale testing and other testing plans."""

import logging

from abmlux.sim_time import DeferredEventPool
import abmlux.random_tools as random_tools
from abmlux.interventions import Intervention

log = logging.getLogger("testing")

# This file uses callbacks and interfaces which make this hit many false positives
#pylint: disable=unused-argument
class LargeScaleTesting(Intervention):
    """Randomly select a number of people per day for testing."""

    def __init__(self, prng, config, clock, bus, state, init_enabled):
        super().__init__(prng, config, clock, bus, init_enabled)

        self.agents_tested_per_day_raw        = config['tests_per_day']
        self.invitation_to_test_booking_delay = \
            int(clock.days_to_ticks(config['invitation_to_test_booking_days']))

        scale_factor = state.config['n'] / sum(state.config['age_distribution'])
        self.agents_tested_per_day = max(int(self.agents_tested_per_day_raw * scale_factor), 1)

        self.test_booking_events = DeferredEventPool(bus, clock)
        self.network = state.network
        self.current_day = None

        self.bus.subscribe("notify.time.midnight", self.midnight, self)

    def midnight(self, clock, t):
        """At midnight, book agents in for testing after a given delay by queuing up events
        that request a test be booked.

        This is equivalent to agents being notified that they should book, but not doing so
        immediately."""

        if not self.enabled:
            return

        # Invite for testing by random selection:
        test_agents_random = random_tools.random_sample(self.prng, self.network.agents,
                                                        self.agents_tested_per_day)
        for agent in test_agents_random:
            self.test_booking_events.add("request.testing.book_test", \
                                         self.invitation_to_test_booking_delay, agent)

class OtherTesting(Intervention):
    """This refers to situations where an agent books a test without having been directed to do so
    by any of the other interventions. Chief among these are the situations in which an agent
    voluntarily books a test having developed symptoms."""

    def __init__(self, prng, config, clock, bus, state, init_enabled):
        super().__init__(prng, config, clock, bus, init_enabled)

        self.prob_test_symptoms                = config['prob_test_symptoms']
        self.onset_of_symptoms_to_test_booking = \
            int(clock.days_to_ticks(config['onset_of_symptoms_to_test_booking_days']))

        self.symptomatic_states  = set(config['symptomatic_states'])
        self.test_booking_events = DeferredEventPool(bus, clock)

        self.bus.subscribe("notify.agent.health", self.handle_health_change, self)


    def handle_health_change(self, agent, old_health):
        """When an agent changes health state to a symptomatic state, there is a certain chance
        that they book a test.  Booking a test takes time, so this method queues up the test
        booking event."""

        if not self.enabled:
            return

        # If no change, skip
        if old_health == agent.health:
            return

        # If moving from an asymptomatic state to a symtomatic state
        if old_health not in self.symptomatic_states and agent.health in self.symptomatic_states:
            if random_tools.boolean(self.prng, self.prob_test_symptoms):
                self.test_booking_events.add("request.testing.book_test", \
                                             self.onset_of_symptoms_to_test_booking, agent)
