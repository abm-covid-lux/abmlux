
class Location:
  """Represents a location to the system"""

  def __init__(self, typ, coord, who=None):
    # FIXME: document this.
    self.typ   = typ
    self.coord = coord
    self.who   = who
