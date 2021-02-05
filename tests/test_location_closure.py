"""Test the location closure intervention"""

import unittest

from abmlux.agent import Agent
from abmlux.location import Location
from abmlux.utils import instantiate_class

from abmlux.messagebus import MessageBus

class TestLocationClosure(unittest.TestCase):
    """Test the location closure intervention"""

    def test_enabled(self):
        """Test that distance function works correctly"""

        intervention_config = {"__type__": "location_closure.LocationClosures", "__prng_seed__": 1,
        "__enabled__": False, "__schedule__": ["16th March 2020: enable", "25th May 2020: disable"],
        "locations": "Primary School", "home_activity_type": "House"}

        intervention_class = intervention_config['__type__']

        initial_enabled = False if '__enabled__' in intervention_config and \
                          not intervention_config['__enabled__'] else True

        new_intervention = instantiate_class("abmlux.interventions", intervention_class,
                                             intervention_config, initial_enabled)

        assert not new_intervention.enabled

        new_intervention.enable()

        assert new_intervention.enabled

    def test_handle_location_change(self):
        """Test that distance function works correctly"""

        intervention_config = {"__type__": "location_closure.LocationClosures", "__prng_seed__": 1,
        "__enabled__": True, "__schedule__": ["16th March 2020: enable", "25th May 2020: disable"],
        "locations": "Primary School", "home_activity_type": "House"}

        intervention_class = intervention_config['__type__']

        initial_enabled = False if '__enabled__' in intervention_config and \
                          not intervention_config['__enabled__'] else True

        new_intervention = instantiate_class("abmlux.interventions", intervention_class,
                                             intervention_config, initial_enabled)

        test_current_location = Location("Test type", (0,0))
        test_agent = Agent(40, "Luxembourg", test_current_location)

        test_home_location = Location("House", (1,1))
        test_agent.add_activity_location(0, test_home_location)

        test_new_location_1 = Location("Primary School", (2,2))
        test_new_location_2 = Location("Not a Primary School", (2,2))

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

        assert new_intervention.handle_location_change(test_agent, test_new_location_1)

        assert not new_intervention.handle_location_change(test_agent, test_new_location_2)
