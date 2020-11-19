"""Module for working with a population density map.

In ABMLUX population density maps are used to initialise locations with realistic distances
to one another, which in turn defines where people are located in space."""

import logging

import numpy as np

from abmlux.world.map import DensityMap
from abmlux.world.map_factory import MapFactory
from abmlux.random_tools import Random

# Module log
log = logging.getLogger('uniform_map_factory')


class UniformMapFactory(MapFactory):
    """Uses a uniform rectangular density to return a DensityMap"""

    def __init__(self, random_seed, country_code, width_m, height_m):

        """Return a two-dimensional array containing uniform population density weights"""

        self.country_width  = width_m
        self.country_height = height_m
        self.country_code   = country_code
        log.info("Country with code %s has %ix%im of data", \
                 country_code, self.country_width, self.country_height)

        self.prng = Random(random_seed)

    def get_map(self) -> DensityMap:

        # Map the grid coordinates given onto a cartesian grid, each cell
        # of which represents the population density at that point
        log.debug("Building density matrix...")
        country = DensityMap(self.prng, 0, 0, self.country_width, self.country_height, 1000)

        country.density = np.ones((self.country_width/country.cell_size_m,
                                   self.country_height/country.cell_size_m), dtype=int)
        country.force_recompute_marginals()

        return country
