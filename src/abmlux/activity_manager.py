"""Mechanisms to work with activity types, and convert them between human-readable strings
and ints used for indexing.

Activities are configured as strings, but may be represented in code as ints for speed
and memory usage reasons.
"""

import logging
import functools
from typing import Union

log = logging.getLogger("activity")

# Stop pylint from complaining about typehints
# pylint: disable=unsubscriptable-object
class ActivityManager:
    """Encapsulates activity configuration, and offers methods to map between different
    representations of those activities."""

    def __init__(self, activity_map_config: dict):
        self.map_config = activity_map_config
        log.debug("Raw mapping: %s", self.map_config)

        # Build lookup tables
        self.str_to_int = {}
        self.int_to_str = {}
        for i, k in enumerate(self.map_config.keys()):
            self.int_to_str[i] = k
            self.str_to_int[k] = i

        log.debug("Map int->str: %s", self.int_to_str)
        log.debug("Map str->int: %s", self.str_to_int)

    def types_as_int(self) -> list[int]:
        """Return the list of all types as integers.

        The ordering of the response will be the same as types_as_str"""
        return list(self.int_to_str.keys())

    def types_as_str(self) -> list[int]:
        """Return a list of all types as strings.

        If types_as_int is also called, the ordering will be the same."""
        return list(self.str_to_int.keys())

    @functools.lru_cache(maxsize=256)
    def as_int(self, str_or_int: Union[str, int]) -> int:
        """Given a string or int representation of an activity type,
        return the representation as an integer.

        Parameters:
            str_or_int: The activity type to return as an int"""
        if isinstance(str_or_int, int):
            return str_or_int

        return self.str_to_int[str_or_int]

    @functools.lru_cache(maxsize=128)
    def as_str(self, str_or_int: Union[str, int]) -> str:
        """Given a string or int representation of an activity type,
        return the representation as a string.

        Parameters:
            str_or_int: The activity type to return as a string"""
        if isinstance(str_or_int, str):
            return str_or_int

        return self.int_to_str[str_or_int]

    @functools.lru_cache(maxsize=256)
    def get_location_types(self, activity_type: Union[str, int]) -> list[int]:
        """For a given activity type int, return a list of
        location types that can be used by agents to perform this activity."""

        activity_type = self.as_str(activity_type)

        log.debug("Finding location types for activity_type '%s'", activity_type)

        # Look up from config using the name
        if activity_type in self.map_config:
            return self.map_config[activity_type]
        return []
