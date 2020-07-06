
import uuid

class Location:
    """Represents a location to the system"""

    def __init__(self, typ, coord, attendees=None):
        # FIXME: document this.
        #
        self.uuid      = uuid.uuid4().hex
        self.typ       = typ
        self.coord     = coord

        # Who is currently at the location
        self.attendees = set() if attendees is None else attendees

    def set_coordinates(self, x, y=None):
        """Set coordinates for this location.

        Accepts x, y as two arguments, or as a single
        tuple or list of [x,y] with None as the second
        arg."""

        if isinstance(x, (list, tuple)) and y is None:
            y = x[1]
            x = x[0]

        self.coord = (x, y)

    def __str__(self):
        return (f"{self.typ}[{self.uuid}]")
