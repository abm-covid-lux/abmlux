"""Represents large scale testing and other testing plans."""

import math
import logging
from tqdm import tqdm
from collections import deque, defaultdict

from abmlux.sim_time import DeferredEventPool
import abmlux.random_tools as random_tools
from abmlux.interventions import Intervention

log = logging.getLogger("testing")

class LargeScaleTesting(Intervention):
    """Select n people per day for testing at random"""

    def __init__(self, prng, config, clock, bus, state):
        super().__init__(prng, config, clock, bus)

        self.agents_tested_per_day                = config['large_scale_testing']['tests_per_day']
        self.invitation_sent_to_test_booking_days = config['large_scale_testing']['invitation_sent_to_test_booking_days']

        # Parameters
        # self.symptomatic_states  = set(config['symptomatic_states'])
        self.network = state.network
       
        self.current_day = None
        
        self.bus.subscribe("sim.time.midnight", self.midnight)

    def midnight(self, clock, t):

        # Invited for testing by random selection:
        test_agents_random = random_tools.random_sample(self.prng, self.network.agents,
                                                        self.agents_tested_per_day)            # How many to test per day. Numbers such as these need rescaling by population size!
        for agent in test_agents_random:
            self.bus.publish('testing.selected', agent)


                    #if not information['awaiting test'][agent]:
                    #    delay_days = random_tools.multinoulli(self.prng, [0.007, 0.0935, 0.355, 0.3105, 0.1675, 0.055, 0.0105, 0.001])
                    #    delay_ticks = max(int(sim.clock.days_to_ticks(delay_days)), 1)
                    #    schedule['testing'][t + delay_ticks].add(agent)


class OtherTesting(Intervention):
    """Other testing"""

    def __init__(self, prng, config, clock, bus, state):
        super().__init__(prng, config, clock, bus)

        self.prob_test_symptoms                     = config['other_testing']['prob_test_symptoms']
        self.onset_of_symptoms_to_test_booking_days = config['other_testing']['onset_of_symptoms_to_test_booking_days']