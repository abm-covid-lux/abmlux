

import abmlux.utils as utils

class Network:

    def __init__(self):

        self.agents    = []
        self.locations = []

        self.agents_by_type    = {}
        self.locations_by_type = {}

    def add_agent(self, agent):
        self.agents.append(agent)

        # Create the list if it ain't there yet.
        if agent.agetyp not in self.agents_by_type:
            self.agents_by_type[agent.agetyp] = []

        self.agents_by_type[agent.agetyp].append(agent)


    def add_location(self, location):
        self.locations.append(location)

        if location.typ not in self.locations_by_type:
            self.locations_by_type[location.typ] = []

        self.locations_by_type[location.typ].append(location)


    def count(self, location_type):
        if location_type not in self.locations_by_type:
            return 0
        return len(self.locations_by_type[location_type])




    def locations_for_types(self, location_types):
        """Return a list of allowable locations for all of the types
        given.

        location_types may be a string, or a list of strings."""

        if isinstance(location_types, str):
            location_types = [location_types]

        stuff = [self.locations_by_type[lt] for lt in location_types]
        return utils.flatten(stuff)



