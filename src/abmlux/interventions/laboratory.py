"""Represents laboratory testing and test booking system."""

import logging

from abmlux.sim_time import DeferredEventPool
from abmlux.interventions import Intervention

log = logging.getLogger("laboratory")

# This file uses callbacks and interfaces which make this hit many false positives
#pylint: disable=unused-argument
class Laboratory(Intervention):
    """A testing laboratory."""

    def __init__(self, prng, config, clock, bus, state, init_enabled):
        super().__init__(prng, config, clock, bus, init_enabled)

        self.prob_false_positive = config['prob_false_positive']
        self.prob_false_negative = config['prob_false_negative']

        self.do_test_to_test_results_ticks = \
            int(clock.days_to_ticks(config['do_test_to_test_results_days']))
        self.infected_states = \
            set(config['incubating_states']).union(set(config['contagious_states']))

        self.test_result_events = DeferredEventPool(bus, clock)

        self.bus.subscribe("request.testing.start", self.start_test, self)

    def start_test(self, agent):
        """Start the test.

        Agents are tested by selecting a weighted random result according to the class' config,
        and then queueing up a result to be sent out after a set amount of time.  This delay
        represents the time taken to complete the test itself.
        """

        # If disabled, don't start new tests.  Tests underway will still complete
        if not self.enabled:
            return

        test_result = False
        if agent.health in self.infected_states:
            if self.prng.boolean(1 - self.prob_false_negative):
                test_result = True
        else:
            if self.prng.boolean(self.prob_false_positive):
                test_result = True

        self.test_result_events.add("notify.testing.result", self.do_test_to_test_results_ticks, agent, test_result)


class TestBooking(Intervention):
    """Consume a 'request to book test' signal and wait a bit whilst getting around to it.

    Represents the process of booking a test, where testing may be limited and not available
    immediately."""

    def __init__(self, prng, config, clock, bus, state, init_enabled):
        super().__init__(prng, config, clock, bus, init_enabled)

        # Time between selection for test and the time at which the test will take place
        self.time_to_arrange_test_no_symptoms = \
            int(clock.days_to_ticks(config['test_booking_to_test_sample_days_no_symptoms']))
        self.time_to_arrange_test_symptoms    = \
            int(clock.days_to_ticks(config['test_booking_to_test_sample_days_symptoms']))

        self.symptomatic_states   = set(config['symptomatic_states'])
        self.test_events          = DeferredEventPool(bus, clock)
        self.agents_awaiting_test = set()

        self.bus.subscribe("request.testing.book_test", self.handle_book_test, self)

    def handle_book_test(self, agent):
        """Someone has been selected for testing.  Insert a delay between the booking of the test
        and the test"""

        # If disabled, prevent new bookings.  Old bookings will still complete
        if not self.enabled:
            return

        if agent not in self.agents_awaiting_test:
            if agent.health in self.symptomatic_states:
                self.test_events.add(self.send_agent_for_test,
                                     self.time_to_arrange_test_symptoms, agent)
            else:
                self.test_events.add(self.send_agent_for_test,
                                     self.time_to_arrange_test_no_symptoms, agent)
            self.agents_awaiting_test.add(agent)

    def send_agent_for_test(self, agent):
        self.agents_awaiting_test.remove(agent) # Update index
        self.bus.publish("request.testing.start", agent)
