"""Tools for representing locations on the network.

Locations have a type and coordinates in space."""

import uuid

from pyproj import Transformer

# Keep these between runs.  This brings a significant performance improvement
# 4326 is the EPSG identifier of WGS84
# 3035 is the EPSG identifier of ETRS89
_transform_ETRS89_to_WGS84 = Transformer.from_crs('epsg:3035', 'epsg:4326')
_transform_WGS84_to_ETRS89 = Transformer.from_crs('epsg:4326', 'epsg:3035')

LocationTuple = tuple[float, float]

class Location:
    """Represents a location to the system"""

    def __init__(self, typ: str, coord: LocationTuple):
        """Represents a location on the network.

        Parameters:
          typ (str): The type of location, as a string
          etrs89_coord (tuple):2-tuple with x, y grid coordinates in ETRS89 format
        """

        self.uuid  = uuid.uuid4().hex
        self.typ   = typ
        self.coord = coord

        self.wgs84 = ETRS89_to_WGS84(self.coord)

    def __str__(self):
        return f"{self.typ}[{self.uuid}]"

# pylint: disable=invalid-name
def ETRS89_to_WGS84(coord: LocationTuple) -> LocationTuple:
    """Convert from ABMLUX grid format (actually ETRS89) to lat, lon in WGS84 format"""

    return _transform_ETRS89_to_WGS84.transform(coord[1], coord[0])

def WGS84_to_ETRS89(coord: LocationTuple) -> LocationTuple:
    """Convert from lat, lon in WGS84 format to ABMLUX' grid format (ETRS89)"""
    # FIXME: this is inconsistent with ETRS89_to_WGS84, taking lat/lon instead of a tuple

    latitude, longitude = coord
    return _transform_WGS84_to_ETRS89.transform(latitude, longitude)
