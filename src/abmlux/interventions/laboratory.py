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
    """A testing laboratory."""

    def __init__(self, prng, config, clock, bus, state):
        super().__init__(prng, config, clock, bus)

        self.prob_false_positive = config['test_sampling']['prob_false_positive']
        self.prob_false_negative = config['test_sampling']['prob_false_negative']

        self.do_test_to_test_results_ticks = \
            int(clock.days_to_ticks(config['test_sampling']['do_test_to_test_results_days']))
        self.infected_states = \
            set(config['incubating_states']).union(set(config['contagious_states']))
            
        self.test_result_events = DeferredEventPool(bus, clock)

        self.bus.subscribe("testing.do_test", self.handle_do_test)

    def handle_do_test(self, agent):

        test_result = False
        if agent.health in self.infected_states:
            if random_tools.boolean(self.prng, 1 - self.prob_false_negative):
                test_result = True
        else:
            if random_tools.boolean(self.prng, self.prob_false_positive):
                test_result = True

        self.test_result_events.add("testing.result", self.do_test_to_test_results_ticks, agent, test_result)


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

        self.bus.subscribe("testing.book_test", self.handle_book_test)

    def handle_book_test(self, agent):
        """Someone has been selected for testing.  Insert a delay between the booking of the test
        and the test"""

        if agent not in self.agents_awaiting_test:
            if agent.health in self.symptomatic_states:
                self.test_events.add(self.send_agent_for_test, self.time_to_arrange_test_symptoms, agent)
            else:
                self.test_events.add(self.send_agent_for_test, self.time_to_arrange_test_no_symptoms, agent)
            self.agents_awaiting_test.add(agent)

    def send_agent_for_test(self, agent):
        self.agents_awaiting_test.remove(agent) # Update index
        self.bus.publish("testing.do_test", agent)