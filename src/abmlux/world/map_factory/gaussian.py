"""Module for working with a population density map.

In ABMLUX population density maps are used to initialise locations with realistic distances
to one another, which in turn defines where people are located in space."""

import logging

import numpy as np
import scipy.stats as st

from abmlux.world.map import DensityMap
from abmlux.world.map_factory import MapFactory
from abmlux.random_tools import Random

# Module log
log = logging.getLogger('gaussian_map_factory')


class GaussianMapFactory(MapFactory):
    """Returns a square DensityMap with a centered Gaussian concentration of mass"""

    def __init__(self, rand_seed, mass, sd_cluster, country_code, width_m):

        """Return a two-dimensional array containing a centered Gaussian population density"""

        self.country_width  = width_m
        self.country_height = width_m
        self.mass           = mass
        self.sd_cluster     = sd_cluster
        self.country_code   = country_code
        log.info("Country with code %s has %ix%im of data", \
                 country_code, self.country_width, self.country_height)

        self.prng = Random(rand_seed)

    def get_map(self) -> DensityMap:

        # Create square density map object
        log.debug("Building density matrix...")
        country = DensityMap(self.prng, 0, 0, self.country_width, self.country_height, 1000)

        # Create Gaussian density centered at the center of
        # the square with given standard deviation and total mass
        x = np.linspace(-int(self.country_width/(2*country.cell_size_m)),
                         int(self.country_height/(2*country.cell_size_m)),
                             self.country_width/(country.cell_size_m))
        kern1d = np.array(st.norm.pdf(x, 0, self.sd_cluster))
        kern2d = np.outer(kern1d, kern1d)
        normalized = kern2d*(self.mass/kern2d.sum())

        country.density = normalized.astype(int)
        country.force_recompute_marginals()

        return country
