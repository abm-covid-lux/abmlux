"""Test the curfew intervention"""

import unittest
import datetime

from abmlux.agent import Agent
from abmlux.location import Location
from abmlux.utils import instantiate_class
from abmlux.sim_time import SimClock

from abmlux.messagebus import MessageBus

class TestCurfew(unittest.TestCase):
    """Test the curfew intervention"""

    def test_enabled(self):
        """Test that distance function works correctly"""

        intervention_config = {"__type__": "curfew.Curfew", "__prng_seed__": 1,
                               "__enabled__": False, "__schedule__": "26th October 2020",
                               "start_time": 23, "end_time": 6,
                               "locations": ["House", "Care Home", "Restaurant"],
                               "home_activity_type": "House"}

        intervention_class = intervention_config['__type__']

        initial_enabled = False if '__enabled__' in intervention_config and \
                          not intervention_config['__enabled__'] else True

        new_intervention = instantiate_class("abmlux.interventions", intervention_class,
                                             intervention_config, initial_enabled)

        assert not new_intervention.enabled

        new_intervention.enable()

        assert new_intervention.enabled

        new_intervention.active = True

        assert new_intervention.active

        new_intervention.active = False

        assert not new_intervention.active

    def test_handle_location_change(self):
        """Test that distance function works correctly"""

        intervention_config = {"__type__": "curfew.Curfew", "__prng_seed__": 1,
                                "__enabled__": False, "__schedule__": "26th October 2020",
                                "start_time": 23, "end_time": 6,
                                "locations": ["House", "Care Home", "Restaurant"],
                                "home_activity_type": "House"}

        intervention_class = intervention_config['__type__']

        initial_enabled = False if '__enabled__' in intervention_config and \
                            not intervention_config['__enabled__'] else True

        new_intervention = instantiate_class("abmlux.interventions", intervention_class,
                                                intervention_config, initial_enabled)

        test_current_location = Location("Test type", (0,0))
        test_agent = Agent(40, "Luxembourg", test_current_location)

        test_home_location = Location("House", (1,1))
        test_agent.add_activity_location(0, test_home_location)

        test_new_location_1 = Location("Restaurant", (2,2))
        test_new_location_2 = Location("Not a Restaurant", (2,2))

        def test_callback(agent, home_location):
            """Test callback function"""
            if home_location == agent.locations_for_activity(0)[0]:
                result = True
            else:
                result = False
            return result

        test_bus = MessageBus()

        test_bus.handlers["request.agent.location"].append( (test_callback, None) )

        new_intervention.bus = test_bus
        new_intervention.home_activity_type = 0

        new_intervention.enabled = True
        new_intervention.active = True

        assert new_intervention.handle_location_change(test_agent, test_new_location_1)

        assert not new_intervention.handle_location_change(test_agent, test_new_location_2)

        assert new_intervention.start_time == datetime.time(23)

        assert new_intervention.end_time != datetime.time(5)

        epoch = "12th December 2004"
        test_clock = SimClock(600, 10, epoch)

        new_intervention.handle_time_change(test_clock, 12)

        assert new_intervention.active

        epoch = "11:14, 12th December 2004"
        test_clock = SimClock(600, 10, epoch)

        new_intervention.handle_time_change(test_clock, 12)

        assert not new_intervention.active
