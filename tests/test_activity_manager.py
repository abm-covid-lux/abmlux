

from abmlux.activity_manager import ActivityManager

SAMPLE_CONFIG = {'House': ['House', 'Care Home', 'Belgium', 'France', 'Germany'], 'Work': ['Care Home', 'OW Agriculture', 'OW Extraction', 'OW Manufacturing', 'OW Energy', 'OW Water', 'OW Construction', 'OW Trade', 'OW Transport', 'OW Catering and Accommodation', 'OW ICT', 'OW Finance', 'OW Real Estate', 'OW Technical', 'OW Administration', 'OW Education', 'OW Entertainment', 'OW Other Services', 'Primary School', 'Secondary School', 'Restaurant', 'Public Transport', 'Shop', 'Medical', 'Hospital', 'Hotel', 'Place of Worship', 'Indoor Sport', 'Cinema or Theatre', 'Museum or Zoo'], 'School': ['Primary School', 'Secondary School'], 'Restaurant': ['Restaurant'], 'Outdoor': ['Outdoor'], 'Car': ['Car'], 'Public Transport': ['Public Transport'], 'Shop': ['Shop'], 'Medical': ['Medical'], 'Place of Worship': ['Place of Worship'], 'Indoor Sport': ['Indoor Sport'], 'Cinema or Theatre': ['Cinema or Theatre'], 'Museum or Zoo': ['Museum or Zoo'], 'Visit': ['House', 'Care Home']}

class TestActivityManager:
    """Tests the ActivityManager class in abmlux.activity_manager"""

    def test_activity_mapping(self):
        """Ensure the mapping between strings and ints is consistent"""

        am = ActivityManager(SAMPLE_CONFIG)

        # Test the numbering of types, should convert back and
        # forth just fine
        for i, label in enumerate(SAMPLE_CONFIG.keys()):
            assert(i == am.as_int(label))
            assert(label == am.as_str(i))

        # Ensure all the types are the same
        assert(list(SAMPLE_CONFIG.keys()) == list(am.types_as_str()))

    def test_types_as_int(self):
        """Checks conversion of activities to int format"""

        am = ActivityManager(SAMPLE_CONFIG)
        assert(am.types_as_int() == [0,1,2,3,4,5,6,7,8,9,10,11,12,13])

    def test_types_as_str(self):
        """Checks conversion of activities to str format"""

        am = ActivityManager(SAMPLE_CONFIG)
        assert(am.types_as_str() == ['House', 'Work', 'School', 'Restaurant', 'Outdoor', 'Car', 'Public Transport', 'Shop', 'Medical', 'Place of Worship', 'Indoor Sport', 'Cinema or Theatre', 'Museum or Zoo', 'Visit'])

    def test_as_int(self):
        """Checks names of activities"""

        am = ActivityManager(SAMPLE_CONFIG)
        assert(am.as_int("House") == 0)

    def test_as_str(self):
        """Checks names of activities"""

        am = ActivityManager(SAMPLE_CONFIG)
        assert(am.as_str(0) == 'House')

    def test_get_location_types(self):
        """Checks that we can look up location types from actvities"""

        am = ActivityManager(SAMPLE_CONFIG)

        # Should return one item
        assert(am.get_location_types("House") == ['House', 'Care Home', 'Belgium', 'France', 'Germany'])

        # Should return >1 item
        assert(am.get_location_types("Work") == ['Care Home', 'OW Agriculture', 'OW Extraction', 'OW Manufacturing', 'OW Energy', 'OW Water', 'OW Construction', 'OW Trade', 'OW Transport', 'OW Catering and Accommodation', 'OW ICT', 'OW Finance', 'OW Real Estate', 'OW Technical', 'OW Administration', 'OW Education', 'OW Entertainment', 'OW Other Services', 'Primary School', 'Secondary School', 'Restaurant', 'Public Transport', 'Shop', 'Medical', 'Hospital', 'Hotel', 'Place of Worship', 'Indoor Sport', 'Cinema or Theatre', 'Museum or Zoo'])

        # Should return an empty list
        assert(am.get_location_types("__NULL__") == [])