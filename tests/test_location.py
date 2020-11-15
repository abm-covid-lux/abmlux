"""Test location storage and coordinate conversion"""

import unittest

from abmlux.location import Location, ETRS89_to_WGS84, WGS84_to_ETRS89

class TestLocation(unittest.TestCase):

    def test_location_creation(self):

        location = Location("LocationType", (10, 10))

        assert location.typ == "LocationType"
        assert location.coord == (10, 10)

    def test_ETRS89_to_WGS84_conversion(self):
        # Converted using https://tool-online.com/en/coordinate-converter.php

        etrs = (10, 10)
        expected = (12.993702651189356, -29.08677779676835)

        assert expected == ETRS89_to_WGS84(etrs)


    def test_WGS84_to_ETRS89_conversion(self):

        wgs = (10, 10)
        expected = (-1346008.5785293942, 4321000.0)

        assert expected == WGS84_to_ETRS89(wgs)
