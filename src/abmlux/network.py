"""Represents the network of locations."""

from typing import Union

import abmlux.utils as utils
from abmlux.map import Map
from abmlux.agent import Agent, AgentType
from abmlux.location import Location

class Network:
    """Represents the network of locations, upon a map describing their relationship to real life.
    """

    def __init__(self, map_: Map):

        self.map: Map                   = map_
        self.agents: list[Agent]        = []
        self.locations: list[Location]  = []

        self.agents_by_type: dict[AgentType, list[Agent]] = {}
        self.locations_by_type: dict[str, list[Location]] = {}

    def add_agent(self, agent: Agent) -> None:
        """Add an agent to the network.

        Parameters:
            agent: The Agent object to add.
        """
        self.agents.append(agent)

        # Create the list if it ain't there yet.
        if agent.agetyp not in self.agents_by_type:
            self.agents_by_type[agent.agetyp] = []

        self.agents_by_type[agent.agetyp].append(agent)

    def add_location(self, location: Location) -> None:
        """Add a Location object to the network."""

        self.locations.append(location)

        if location.typ not in self.locations_by_type:
            self.locations_by_type[location.typ] = []

        self.locations_by_type[location.typ].append(location)

    def count(self, location_type: str) -> int:
        """Return the number of locations on this network of the type specified"""

        if location_type not in self.locations_by_type:
            return 0
        return len(self.locations_by_type[location_type])

    def locations_for_types(self, location_types: Union[str, list[str]]) -> list[Location]:
        """Return a list of allowable locations for all of the types
        given.

        location_types may be a string, or a list of strings."""

        if isinstance(location_types, str):
            location_types = [location_types]

        stuff = [self.locations_by_type[lt] for lt in location_types]
        return utils.flatten(stuff)
