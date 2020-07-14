"""Tools for representing locations on the network"""

import uuid
from pyproj import Transformer

# Keep these between runs.  This brings a significant performance improvement
# 4326 is the EPSG identifier of WGS84
# 3035 is the EPSG identifier of ETRS89
_transform_ETRS89_to_WGS84 = Transformer.from_crs('epsg:3035', 'epsg:4326')
_transform_WGS84_to_ETRS89 = Transformer.from_crs('epsg:4326', 'epsg:3035')

class Location:
    """Represents a location to the system"""

    def __init__(self, typ, coord, attendees=None):
        """Represents a location on the network.

        Parameters:
          typ (str): The type of location, as a string
          coord (tuple):2-tuple with x, y grid coordinates in ETRS89 format
          attendees (set):Set of Agent objects showing who is here
        """
        self.uuid      = uuid.uuid4().hex
        self.typ       = typ
        self.coord     = coord

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
        return f"{self.typ}[{self.uuid}]"

def ETRS89_to_WGS84(coord):
    """Convert from ABMLUX grid format (actually ETRS89) to lat, lon in WGS84 format"""

    return _transform_ETRS89_to_WGS84.transform(coord[0], coord[1])

def WGS84_to_ETRS89(lat, lon):
    """Convert from lat, lon in WGS84 format to ABMLUX' grid format (ETRS89)"""

    return _transform_WGS84_to_ETRS89.transform(lat, lon)
