"""Representations of a single agent within the system"""

import logging
import uuid
from enum import IntEnum
from collections.abc import Iterable
from typing import Union, Optional

from abmlux.location import Location

log = logging.getLogger("agent")

class Agent:
    """Represents a single agent within the simulation"""

    def __init__(self, age: int, nationality: str, current_location: Union[None, Location]=None):
        # TODO: documentation of argument meaning

        self.uuid                  = uuid.uuid4().hex
        self.age: int              = age
        self.nationality: str      = nationality
        self.behaviour_type: str   = None
        self.activity_locations: dict[str, list[Location]] = {}

        # Current state
        self.current_activity: Optional[str]       = None
        self.current_location: Optional[Location]  = current_location
        self.health: Optional[str]                 = None

    def locations_for_activity(self, activity: str) -> list[Location]:
        """Return a list of locations this agent can go to for
        the activity given"""

        if activity not in self.activity_locations:
            return []

        return self.activity_locations[activity]

    def add_activity_location(self, activity: str, location: Location) -> None:
        """Add a location to the list allowed for a given activity

        Parameters:
            activity: The activity that will be performed
            location: A single location, or a list of locations.
        """

        if activity not in self.activity_locations:
            self.activity_locations[activity] = []  # TODO: maybe use a set?

        # Ensure we can join the lists together if given >1 item
        location_list: list[Location]
        if isinstance(location, Iterable):
            location_list = list(location)
        else:
            location_list = [location]

        self.activity_locations[activity] += location_list

    def set_behaviour_type(self, behaviour_type: str) -> None:
        """Sets the agent as having the given behaviour type"""

        log.debug("Agent %s: Behaviour type %s -> %s", self.uuid, self.behaviour_type, behaviour_type)
        self.behaviour_type = behaviour_type

    def set_health(self, health: str) -> None:
        """Sets the agent as having the given health state"""

        log.debug("Agent %s: Health %s -> %s", self.uuid, self.health, health)
        self.health = health

    def set_activity(self, activity: str) -> None:
        """Sets the agent as performing the activity given"""

        log.debug("Agent %s: Activity %s -> %s", self.uuid, self.current_activity, activity)
        self.current_activity = activity

    def set_location(self, location: Location) -> None:
        """Sets the agent as being in the location specified"""

        log.debug("Agent %s: Location %s -> %s", self.uuid, self.current_location, location)
        self.current_location = location

    def __str__(self):
        return (f"<Agent {self.uuid}; age={self.age}, "
                f"activities={len(self.activity_locations)}, "
                f"current_loc={self.current_location}>")
