

from abmlux.activity_manager import ActivityManager

SAMPLE_CONFIG = {'House': {'primary': [1], 'secondary': [11, 12, 13, 14, 21, 22, 23, 31, 34, 35, 39, 115, 121, 213, 214, 221, 222, 231, 239, 311, 314, 315, 324, 325, 326, 327, 328, 329, 333, 346, 347, 349, 351, 353, 354, 356, 363, 364, 371, 381, 382, 383, 384, 386, 391, 393, 419, 421, 422, 431, 432, 433, 434, 511, 512, 522, 551, 711, 713, 714, 719, 733, 734, 737, 739, 744, 745, 746, 747, 749, 811, 812, 813, 819, 821, 829, 839], 'allowed_locations': ['House']}, 'Work': {'primary': [2], 'secondary': [111], 'allowed_locations': ['Other Work', 'School', 'Restaurant', 'Public Transport', 'Shop', 'Medical', 'Place of Worship', 'Indoor Sport', 'Cinema or Theatre', 'Museum or Zoo']}, 'School': {'primary': [3], 'secondary': [232, 233], 'allowed_locations': ['School']}, 'Restaurant': {'primary': [5], 'secondary': [546, 547], 'allowed_locations': ['Restaurant']}, 'Outdoor': {'primary': [6, 9, 10, 11, 12, 14], 'secondary': [343, 345, 411, 412, 413, 415, 424, 439, 525, 539, 541, 542, 543, 545, 548, 549, 612, 613, 614, 617, 618, 619, 629], 'allowed_locations': ['Outdoor']}, 'Car': {'primary': [13], 'allowed_locations': ['Car']}, 'Public Transport': {'primary': [15, 16, 17, 18, 19], 'allowed_locations': ['Public Transport']}, 'Shop': {'secondary': [361, 362, 366, 367, 368, 369, 425], 'allowed_locations': ['Shop']}, 'Medical': {'secondary': [365], 'allowed_locations': ['Medical']}, 'Place of Worship': {'secondary': [435], 'allowed_locations': ['Place of Worship']}, 'Indoor Sport': {'secondary': [544, 615, 616], 'allowed_locations': ['Indoor Sport']}, 'Cinema or Theatre': {'secondary': [531, 532, 533], 'allowed_locations': ['Cinema or Theatre']}, 'Museum or Zoo': {'secondary': [534], 'allowed_locations': ['Museum or Zoo']}, 'Other House': {'primary': [4], 'secondary': [395, 426, 429, 515, 521, 523, 524], 'allowed_locations': ['House']}}

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

    def test_get_location_types(self):
        """Checks that we can look up location types from actvities"""

        am = ActivityManager(SAMPLE_CONFIG)

        # Should return one item
        assert(am.get_location_types("House") == ['House'])

        # Should return >1 item
        assert(am.get_location_types("Work") == ['Other Work', 'School',
                                                 'Restaurant', 'Public Transport',
                                                 'Shop', 'Medical', 'Place of Worship',
                                                 'Indoor Sport', 'Cinema or Theatre',
                                                 'Museum or Zoo'])

        # Should return an empty list
        assert(am.get_location_types("__NULL__") == [])

