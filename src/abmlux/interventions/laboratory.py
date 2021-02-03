"""Represents laboratory testing and test booking system."""

import logging
import math

from abmlux.sim_time import DeferredEventPool
from abmlux.interventions import Intervention

log = logging.getLogger("laboratory")

# This file uses callbacks and interfaces which make this hit many false positives
#pylint: disable=unused-argument
#pylint: disable=attribute-defined-outside-init
class Laboratory(Intervention):
    """A testing laboratory."""

    def __init__(self, config, init_enabled):
        super().__init__(config, init_enabled)

        self.prob_false_positive = config['prob_false_positive']
        self.prob_false_negative = config['prob_false_negative']

        self.border_countries    = config['border_countries']

        self.tests_performed_today = 0
        self.home_locations_dict   = {}
        self.resident_dict         = {}

        self.register_variable('max_tests_per_day')

    def init_sim(self, sim):

        super().init_sim(sim)

        self.clock = sim.clock
        self.scale_factor = sim.world.scale_factor

        self.home_activity_type = sim.activity_manager.as_int(self.config['home_activity_type'])
        self.max_tests_per_day = self.config['max_tests_per_day']

        self.do_test_to_test_results_ticks = \
            int(sim.clock.days_to_ticks(self.config['do_test_to_test_results_days']))
        self.infected_states = self.config['incubating_states'] + self.config['contagious_states']

        self.agents = sim.world.agents

        # Collect data on agents for telemetry purposes
        for agent in self.agents:
            home_location = agent.locations_for_activity(self.home_activity_type)[0]
            self.home_locations_dict[agent] = home_location
            if home_location.typ in self.border_countries:
                self.resident_dict[agent] = False
            else:
                self.resident_dict[agent] = True

        self.test_result_events = DeferredEventPool(self.bus, self.clock)
        self.bus.subscribe("request.testing.start", self.start_test, self)
        self.bus.subscribe("notify.time.midnight", self.reset_daily_counter, self)

    def reset_daily_counter(self, clock, t):
        """Reset daily test count"""

        self.tests_performed_today = 0

    def start_test(self, agent):
        """Start the test.

        Agents are tested by selecting a weighted random result according to the class' config,
        and then queueing up a result to be sent out after a set amount of time.  This delay
        represents the time taken to complete the test itself.
        """

        # If disabled, don't start new tests.  Tests underway will still complete
        if not self.enabled:
            return

        if self.tests_performed_today >= math.ceil(self.max_tests_per_day * self.scale_factor):
            return

        test_result = False
        if agent.health in self.infected_states:
            if self.prng.boolean(1 - self.prob_false_negative):
                test_result = True
        else:
            if self.prng.boolean(self.prob_false_positive):
                test_result = True

        self.tests_performed_today += 1

        self.test_result_events.add("notify.testing.result",
                                    self.do_test_to_test_results_ticks, agent, test_result)

        self.report("notify.testing.result", self.clock, test_result, agent.age,
                                   self.home_locations_dict[agent].uuid,
                                   self.home_locations_dict[agent].coord,
                                   self.resident_dict[agent])

class TestBooking(Intervention):
    """Consume a 'request to book test' signal and wait a bit whilst getting around to it.

    Represents the process of booking a test, where testing may be limited and not available
    immediately."""

    def __init__(self, config, init_enabled):
        super().__init__(config, init_enabled)

        self.symptomatic_states   = config['symptomatic_states']
        self.agents_awaiting_test = set()

    def init_sim(self, sim):

        super().init_sim(sim)

        self.test_events          = DeferredEventPool(self.bus, sim.clock)
        self.bus.subscribe("request.testing.book_test", self.handle_book_test, self)

        # Time between selection for test and the time at which the test will take place
        self.time_to_arrange_test_no_symptoms = \
           int(sim.clock.days_to_ticks(self.config['test_booking_to_test_sample_days_no_symptoms']))
        self.time_to_arrange_test_symptoms    = \
           int(sim.clock.days_to_ticks(self.config['test_booking_to_test_sample_days_symptoms']))


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
        """Send an event requesting a test for the given agent."""

        self.agents_awaiting_test.remove(agent) # Update index
        self.bus.publish("request.testing.start", agent)
