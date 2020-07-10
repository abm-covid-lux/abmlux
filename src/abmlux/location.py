
from pyproj import Transformer
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

def ETRS89_to_WGS84(coord):

    scale = 1000/config['res_fact']
    
    transformation = Transformer.from_crs('epsg:3035','epsg:4326')
    
    return transformation.transform(coord[0]*scale,coord[1]*scale)
    
def WGS84_to_ETRS89(lat,long):

    scale = 1000/config['res_fact']
    
    #4326 is the EPSG identifier of WGS84
    #3035 is the EPSG identifier of ETRS89
    
    transformation = Transformer.from_crs('epsg:4326','epsg:3035')
    
    return (transformation.transform(lat,long)[0]/scale,
            transformation.transform(lat,long)[1]/scale)
