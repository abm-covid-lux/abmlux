

import logging
import functools

log = logging.getLogger("activity")

class ActivityManager:

    def __init__(self, activity_map_config):
        self.map_config = activity_map_config
        log.debug(f"Raw mapping: {self.map_config}")

        # Build lookup tables
        self.str_to_int = {}
        self.int_to_str = {}
        for i, k in enumerate(self.map_config.keys()):
            self.int_to_str[i] = k
            self.str_to_int[k] = i

        log.debug(f"Map int->str: {self.int_to_str}")
        log.debug(f"Map str->int: {self.str_to_int}")

    def types_as_int(self):
        return self.int_to_str.keys()

    def types_as_str(self):
        return self.str_to_int.keys()

    @functools.lru_cache(maxsize=128)
    def name(self, activity_type):
        return self.as_str(activity_type)

    @functools.lru_cache(maxsize=128)
    def as_int(self, str_or_int):
        if isinstance(str_or_int, int):
            return str_or_int

        return self.str_to_int[str_or_int]

    @functools.lru_cache(maxsize=128)
    def as_str(self, str_or_int):
        if isinstance(str_or_int, str):
            return str_or_int

        return self.int_to_str[str_or_int]

    @functools.lru_cache(maxsize=128)
    def get_location_types(self, activity_type):
        """For a given activity type (int or enum), return a list of
        location types that can be used by agents to perform this activity."""

        activity_type = self.as_str(activity_type)

        log.debug(f"Finding location types for activity_type '{activity_type}'")

        # Look up from config using the name
        if activity_type in self.map_config and 'allowed_locations' in self.map_config[activity_type]:
            return self.map_config[activity_type]['allowed_locations']
        return []

