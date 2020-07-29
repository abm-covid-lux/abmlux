
import logging
import uuid
from enum import IntEnum
from collections.abc import Iterable


log = logging.getLogger("agent")

class AgentType(IntEnum):
    """Represents a type for each agent."""

    CHILD   = 0
    ADULT   = 1
    RETIRED = 2


class HealthStatus(IntEnum):
    """Agent health status"""

    SUSCEPTIBLE = 0
    INFECTED    = 1
    EXPOSED     = 2
    RECOVERED   = 3
    DEAD        = 4


# TODO: move to config
POPULATION_SLICES = {
        AgentType.CHILD: slice(None, 18),   # Children <18
        AgentType.ADULT: slice(18, 65),     # Adults 18-65
        AgentType.RETIRED: slice(65, None)  # Retired >65
    }
# TODO: de-duplicate
POPULATION_RANGES = {
        AgentType.CHILD: range(0, 18),   # Children <18
        AgentType.ADULT: range(18, 65),     # Adults 18-65
        AgentType.RETIRED: range(65, 120)  # Retired >65
    }




class Agent:
    """Represents a single agent within the simulation"""

    def __init__(self, agetyp, age, current_location=None):
        # TODO: documentation of argument meaning

        self.uuid               = uuid.uuid4().hex
        self.agetyp             = agetyp  # Should be an AgentType
        self.age                = age
        self.activity_locations = {}

        # Current state
        self.current_activity  = None
        self.current_location  = current_location
        self.health            = HealthStatus.SUSCEPTIBLE

    def locations_for_activity(self, activity):
        """Return a list of locations this agent can go to for
        the activity given"""

        if activity not in self.activity_locations:
            return []

        return self.activity_locations[activity]

    def add_activity_location(self, activity, location):
        """Add a location to the list allowed for a given activity"""

        if activity not in self.activity_locations:
            self.activity_locations[activity] = []  # TODO: maybe use a set?

        # Ensure we can join the lists together if given >1 item
        if isinstance(location, Iterable):
            location = list(location)
        else:
            location = [location]

        self.activity_locations[activity] += location

    def set_activity(self, activity, location=None):
        """Sets the agent as performing the activity given at the location
        specified.

        If a location is given, the agent will remove itself from
        any attendee list at the current location, and add itself
        to the attendee list at the new location"""

        log.debug("Agent %s: Activity %s -> %s, Location %s -> %s",
                  self.uuid, self.current_activity, activity, self.current_location, location)
        self.current_activity = activity
        self.current_location = location

    def __str__(self):
        return (f"<Agent {self.uuid}; age={self.age}, "
                f"activities={len(self.activity_locations)}, "
                f"current_loc={self.current_location}>")
