
import uuid
from enum import IntEnum



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

    def __init__(self, agetyp, age, current_location=None, workplace=None):
        # TODO: documentation of argument meaning

        self.uuid              = uuid.uuid4().hex
        self.agetyp            = agetyp  # Should be an AgentType
        self.age               = age
        self.allowed_locations = set()
        self.workplace         = None
        self.home              = None

        self.current_activity  = None
        self.current_location  = current_location
        self.health            = HealthStatus.SUSCEPTIBLE

    def set_activity(self, activity, location=None):
        """Sets the agent as performing the activity given at the location
        specified.

        If a location is given, the agent will remove itself from
        any attendee list at the current location, and add itself
        to the attendee list at the new location"""

        self.current_activity = activity

        # If a location is given, update this too.
        #
        # Be aware that this updates the location itself.
        if location:
            # Remove self from current location
            if self.current_location is not None \
               and self in self.current_location.attendees:
                self.current_location.attendees.remove(self)

            # add self to new location
            self.current_location = location
            location.attendees.add(self)

    def set_home(self, location):
        if self.home is not None:
            self.remove_allowed_location(self.home)
            location.remove_occupant(self)

        self.home = location
        location.add_occupant(self)

        if not location in self.allowed_locations:
            self.add_allowed_location(location)

    def set_workplace(self, location):
        if self.workplace is not None:
            self.remove_allowed_location(self.workplace)

        self.workplace = location

        if not location in self.allowed_locations:
            self.add_allowed_location(location)

    def find_allowed_locations_by_type(self, location_type):
        """Return a set of all locations matching the given type.

        location_type may be a string identifying a single location type,
        or any collection supporting 'in', listing any allowed locations."""

        # If a simple string
        if isinstance(location_type, str):
            return set([x for x in self.allowed_locations if x.typ == location_type])

        # If a list type
        return set([x for x in self.allowed_locations if x.typ in location_type])

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
                f"current_loc={self.current_location}>")
