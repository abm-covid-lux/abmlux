"""Test the stochastic world model"""

import unittest
from abmlux.agent import Agent
from abmlux.location import Location
from abmlux.activity_manager import ActivityManager
from abmlux.world import World
from abmlux.world.world_factory import WorldFactory

from abmlux.world.map_factory.uniform import UniformMapFactory
from abmlux.world.world_factory.stochastic import StochasticWorldFactory

class TestStochasticWorldFactory(unittest.TestCase):
    """Test the stochastic world model"""

    def test_fdsfdss(self):

        TEST_ACTIVITY_MANAGER_CONFIG = {'House': ['House', 'Care Home', 'Belgium', 'France', 'Germany'], 'Work': ['Care Home', 'OW Agriculture', 'OW Extraction', 'OW Manufacturing', 'OW Energy', 'OW Water', 'OW Construction', 'OW Trade', 'OW Transport', 'OW Catering and Accommodation', 'OW ICT', 'OW Finance', 'OW Real Estate', 'OW Technical', 'OW Administration', 'OW Education', 'OW Entertainment', 'OW Other Services', 'Primary School', 'Secondary School', 'Restaurant', 'Public Transport', 'Shop', 'Medical', 'Hospital', 'Hotel', 'Place of Worship', 'Indoor Sport', 'Cinema or Theatre', 'Museum or Zoo'], 'School': ['Primary School', 'Secondary School'], 'Restaurant': ['Restaurant'], 'Outdoor': ['Outdoor'], 'Car': ['Car'], 'Public Transport': ['Public Transport'], 'Shop': ['Shop'], 'Medical': ['Medical'], 'Place of Worship': ['Place of Worship'], 'Indoor Sport': ['Indoor Sport'], 'Cinema or Theatre': ['Cinema or Theatre'], 'Museum or Zoo': ['Museum or Zoo'], 'Visit': ['House', 'Care Home']}

        test_activity_manager = ActivityManager(TEST_ACTIVITY_MANAGER_CONFIG)

        _map = UniformMapFactory(212, "UNI", 10000, 10000)

        world = World(_map)

        TEST_STOCHASTIC_WORLD_FACTORY_CONFIG = {'random_seed': 323, 'age_distribution': [4,5,6], 'n': 15, 'resident_nationality': 'Luxembourg', 'location_choice_fp': 'Scenarios/Luxembourg/Lux Mobil.csv'}

        test_world_factory = StochasticWorldFactory(_map, test_activity_manager, TEST_STOCHASTIC_WORLD_FACTORY_CONFIG)

        test_world_factory._create_agents(world, TEST_STOCHASTIC_WORLD_FACTORY_CONFIG['resident_nationality'])

        assert len(world.agents) == 15

