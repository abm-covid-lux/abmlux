"""Represents laboratory testing and test booking system."""

import math
import logging
from tqdm import tqdm
from collections import deque, defaultdict

from abmlux.sim_time import DeferredEventPool
import abmlux.random_tools as random_tools
from abmlux.interventions import Intervention

log = logging.getLogger("laboratory")

class Laboratory(Intervention):

    def __init__(self, prng, config, clock, bus, state):
        super().__init__(prng, config, clock, bus)

        self.prob_false_positive              = config['test_sampling']['prob_false_positive']
        self.prob_false_negative              = config['test_sampling']['prob_false_negative']
        self.test_sample_to_test_results_days = config['test_sampling']['test_sample_to_test_results_days']

        self.incubating_states = set(config['incubating_states'])
        self.contagious_states = set(config['contagious_states'])

        self.test_sample_to_test_results_ticks = int(clock.days_to_ticks(self.test_sample_to_test_results_days))
        self.infected_states = self.incubating_states.union(self.contagious_states)

        self.test_result_events = DeferredEventPool(bus, clock)
        self.agents_awaiting_results = set()

        self.bus.subscribe("testing.booked", self.handle_testing_booked)
        self.bus.subscribe("laboratory.send_result", self.send_result)

    def handle_testing_booked(self, agent):
        if agent in self.agents_awaiting_results:
            return

        test_result = False
        if agent.health in self.infected_states:
            if random_tools.boolean(self.prng, 1 - self.prob_false_negative):
                test_result = True
        else:
            if random_tools.boolean(self.prng, self.prob_false_positive):
                test_result = True

        self.agents_awaiting_results.add(agent) # Update index
        self.test_result_events.add("laboratory.send_result", self.test_sample_to_test_results_ticks, agent, test_result)
            
    def send_result(self, agent, result):

        # Notify people if time is up
        self.agents_awaiting_results.remove(agent)
        self.bus.publish("testing.result", agent, result)


class TestBooking(Intervention):
    """Consume a 'selected for testing' signal and wait a bit whilst getting around to it"""

    def __init__(self, prng, config, clock, bus, state):
        super().__init__(prng, config, clock, bus)

        # Time between selection for test and the time at which the test will take place
        self.time_to_arrange_test_no_symptoms = int(clock.days_to_ticks(config['test_booking']['test_booking_to_test_sample_days_no_symptoms']))
        self.time_to_arrange_test_symptoms    = int(clock.days_to_ticks(config['test_booking']['test_booking_to_test_sample_days_symptoms']))

        self.symptomatic_states   = set(config['symptomatic_states'])
        self.test_events          = DeferredEventPool(bus, clock)
        self.agents_awaiting_test = set()

        self.bus.subscribe("testing.selected", self.handle_selected_for_testing)
        self.bus.subscribe("test_booking.book_test", self.book_test)

    def handle_selected_for_testing(self, agent):
        """Someone has been selected for testing.  Insert a delay between the booking of the test
        and the test"""

        if agent not in self.agents_awaiting_test:
            if agent.health in self.symptomatic_states:
                self.test_events.add("test_booking.book_test", self.time_to_arrange_test_symptoms, agent)
            else:
                self.test_events.add("test_booking.book_test", self.time_to_arrange_test_no_symptoms, agent)
            self.agents_awaiting_test.add(agent)

    def book_test(self, agent):
        self.agents_awaiting_test.remove(agent) # Update index
        self.bus.publish("testing.booked", agent)