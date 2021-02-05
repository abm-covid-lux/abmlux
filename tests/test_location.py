"""Test the Location object"""

import unittest
from abmlux.location import Location

class TestLocation(unittest.TestCase):
    """Test the location object, which stores location config"""

    def test_distance_euclidean(self):
        """Test that distance function works correctly"""

        test_location_1 = Location("Test type", (0,0))
        test_location_2 = Location("Test type", (3,4))

        assert test_location_1.distance_euclidean(test_location_2) == 5.0
