"""Represents the space in which the network exists"""

import logging

import shapefile

from abmlux.location import ETRS89_to_WGS84
import abmlux.random_tools as random_tools

log = logging.getLogger("map")

class Map:
    """Represents an area to the system.

    This is a square area addressed in ETRS89 format by default.
    """

    def __init__(self, coord, width_km, height_km, shapefilename=None):

        self.coord     = coord
        self.wgs84     = ETRS89_to_WGS84(coord)
        self.width_km  = width_km
        self.height_km = height_km

        self.border = None
        if shapefilename is not None:
            log.info("Loading shapefile from %s...", shapefilename)
            self.border = shapefile.Reader(shapefilename)

    def width(self):
        """Return the width in km"""
        return self.width_km

    def height(self):
        """Return the height in km"""
        return self.height_km

    def __str__(self):
        return f"<{self.__class__.__name__} {self.coord=} {self.width()}x{self.height()}km>"



class DensityMap(Map):
    """A Map that contains population density information"""

    def __init__(self, coord, width_km, height_km, resolution_km, shapefilename=None):

        super().__init__(coord, width_km, height_km, shapefilename)

        self.resolution_km = resolution_km
        self.cell_size_km  = 1 / self.resolution_km
        self.density       = [[0 for x in range(width_km * resolution_km)]
                              for y in range(height_km * resolution_km)]
        self._recompute_marginals()

    def width_grid(self):
        """Return the width in grid cells"""
        return len(self.density[0])

    def height_grid(self):
        """Return the height in grid cells"""
        return len(self.density)

    def set_density(self, x, y, dens):
        """Set the population density at a given grid cell"""
        self.density[y][x] = dens
        self._recompute_marginals()

    def get_density(self, x, y):
        """Return the population density at a given grid cell"""
        return self.density[y][x]

    def sample_coord(self):
        """Return a random sample weighted by density"""

        # Randomly select a cell
        grid_x, grid_y = random_tools.multinoulli_2d(self.density, self.marginals_cache)

        # Uniform random within the cell (fractional component)
        x = self.coord[0] + self.cell_size_km*grid_x + random_tools.random_float(self.cell_size_km)
        y = self.coord[1] + self.cell_size_km*grid_y + random_tools.random_float(self.cell_size_km)

        return x, y

    def _recompute_marginals(self):
        self.marginals_cache = [sum(x) for x in self.density]

    def __str__(self):
        return (f"<{self.__class__.__name__} {self.coord=} {self.width()}x{self.height()}km"
                f" @ {self.resolution_km} cells/km>")
