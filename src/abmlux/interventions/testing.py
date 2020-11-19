"""Represents large scale testing and other testing plans."""

import logging
import math

from abmlux.sim_time import DeferredEventPool
from abmlux.interventions import Intervention

log = logging.getLogger("testing")

# This file uses callbacks and interfaces which make this hit many false positives
#pylint: disable=unused-argument
#pylint: disable=attribute-defined-outside-init
class LargeScaleTesting(Intervention):
    """Randomly select a number of people per day for testing."""

    def init_sim(self, sim):
        super().init_sim(sim)

        self.agents_tested_per_day = math.ceil(sim.world.scale_factor * self.config['tests_per_day'])
        self.invitation_to_test_booking_delay = \
            int(sim.clock.days_to_ticks(self.config['invitation_to_test_booking_days']))

        self.test_booking_events = DeferredEventPool(self.bus, sim.clock)
        self.world               = sim.world
        self.current_day         = None

        self.bus.subscribe("notify.time.midnight", self.midnight, self)

    def midnight(self, clock, t):
        """At midnight, book agents in for testing after a given delay by queuing up events
        that request a test be booked.

        This is equivalent to agents being notified that they should book, but not doing so
        immediately."""

        if not self.enabled:
            return

        # Invite for testing by random selection:
        test_agents_random = self.prng.random_sample(self.world.agents,
                                                     self.agents_tested_per_day)
        for agent in test_agents_random:
            self.test_booking_events.add("request.testing.book_test", \
                                         self.invitation_to_test_booking_delay, agent)

class OtherTesting(Intervention):
    """This refers to situations where an agent books a test without having been directed to do so
    by any of the other interventions. Chief among these are the situations in which an agent
    voluntarily books a test having developed symptoms."""

    def init_sim(self, sim):
        super().init_sim(sim)

        self.prob_test_symptoms                = self.config['prob_test_symptoms']
        self.onset_of_symptoms_to_test_booking = \
            int(sim.clock.days_to_ticks(self.config['onset_of_symptoms_to_test_booking_days']))

        self.symptomatic_states  = set(self.config['symptomatic_states'])
        self.test_booking_events = DeferredEventPool(self.bus, sim.clock)

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
            if self.prng.boolean(self.prob_test_symptoms):
                self.test_booking_events.add("request.testing.book_test", \
                                             self.onset_of_symptoms_to_test_booking, agent)
