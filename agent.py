
import uuid
from enum import IntEnum

class AgentType(IntEnum):
    """Represents a type for each agent."""

    CHILD   = 0
    ADULT   = 1
    RETIRED = 2


class Agent:
    """Represents a single agent within the simulation"""

    def __init__(self, agetyp, age, location=None, workplace=None):
        # TODO: documentation of argument meaning

        self.uuid              = uuid.uuid4().hex
        self.agetyp            = agetyp  # Should be an AgentType
        self.age               = age
        self.location          = location
        self.allowed_locations = set()
        self.workplace         = None
        self.home              = None

    def set_home(self, location):
        if self.home is not None:
            self.remove_allowed_location(self.home)

        self.home = location

        if not location in self.allowed_locations:
            self.add_allowed_location(location)

    def set_workplace(self, location):
        if self.workplace is not None:
            self.remove_allowed_location(self.workplace)

        self.workplace = location

        if not location in self.allowed_locations:
            self.add_allowed_location(location)

    def add_allowed_location(self, location):
        # Allow people to add lists
        if isinstance(location, (list, tuple, set)):
            for loc in location:
                self.add_allowed_location(loc)
            return

        # Add items
        self.allowed_locations.add(location)

    def remove_allowed_location(self, location):
        self.allowed_locations.remove(location)

    def set_allowed_locations(self, allowed_locations):

        self.allowed_locations = allowed_locations

    def is_allowed_location(self, location):

        return location in self.allowed_locations

    def inspect(self):
        return (f"<Agent {self.uuid}; age={self.age}, "
                f"locations={len(self.allowed_locations)}, "
                f"current_loc={self.location}>")
