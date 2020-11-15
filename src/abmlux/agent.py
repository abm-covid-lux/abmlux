"""Representations of a single agent within the system"""

import logging
import uuid
from enum import IntEnum
from collections.abc import Iterable
from typing import Union, Optional

from abmlux.location import Location

log = logging.getLogger("agent")

class AgentType(IntEnum):
    """Represents a type for each agent."""

    CHILD   = 0
    ADULT   = 1
    RETIRED = 2

# TODO: de-duplicate
POPULATION_RANGES = {
        AgentType.CHILD:    range(0, 18),   # Children <18
        AgentType.ADULT:    range(18, 65),  # Adults 18-65
        AgentType.RETIRED:  range(65, 120)  # Retired >65
    }

class Agent:
    """Represents a single agent within the simulation"""

    def __init__(self, age: int, current_location: Union[None, Location]=None):
        # TODO: documentation of argument meaning

        self.uuid               = uuid.uuid4().hex
        self.agetyp: AgentType  = Agent.agent_type_by_age(age)
        self.age: int           = age
        self.activity_locations: dict[str, list[Location]] = {}

        # Current state
        self.current_activity: Optional[str]       = None
        self.current_location: Optional[Location]  = current_location
        self.health: Optional[str]                 = None

    @staticmethod
    def agent_type_by_age(age: int) -> AgentType:
        """Given an age, return the type."""

        for agetyp, rng in POPULATION_RANGES.items():
            if rng.start <= age < rng.stop:
                return agetyp

        raise ValueError(f"No agent type mapping for age {age}")

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
