
import uuid

class Location:
    """Represents a location to the system"""

    def __init__(self, typ, coord, who=None, occupancy=None):
        # FIXME: document this.
        #
        self.uuid      = uuid.uuid4().hex
        self.typ       = typ
        self.coord     = coord
        self.who       = who
        self.occupancy = set() if occupancy is None else occupancy

    def add_occupant(self, agent):
        # Allow people to add lists
        if isinstance(agent, (list, tuple, set)):
            for agt in agent:
                self.add_occupant(agt)
            return

        self.occupancy.add(agent)

    def remove_occupant(self, agent):
        self.occupancy.remove(agent)

    def set_coordinates(self, x, y=None):
        """Set coordinates for this location.

        Accepts x, y as two arguments, or as a single
        tuple or list of [x,y] with None as the second
        arg."""

        if isinstance(x, (list, tuple)) and y is None:
            y = x[1]
            x = x[0]

        self.coord = [x, y]

    def inspect(self):
        return (f"<Location {self.uuid}; type={self.typ}, "
                f"coordinates={self.coord}>")
