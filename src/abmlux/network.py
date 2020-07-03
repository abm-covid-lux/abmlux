



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


