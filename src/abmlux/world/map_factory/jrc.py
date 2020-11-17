"""Module for working with a population density map.

In ABMLUX population density maps are used to initialise locations with realistic distances
to one another, which in turn defines where people are located in space."""

import logging

import pandas as pd
from tqdm import tqdm

from abmlux.world.map import DensityMap
from abmlux.world.map_factory import MapFactory
from abmlux.random_tools import Random

# Module log
log = logging.getLogger('jrc_map_factory')


class JRCMapFactory(MapFactory):
    """Reads JRC-format data and extracts density information to return a DensityMap"""

    def __init__(self, random_seed, population_distribution_fp, country_code, res_fact,
                 normalize_interpolation, shapefilename, shapefile_coord_system):

        """Parse JRC-format country data and return a two-dimensional array
        containing population density weights per-kilometer.

        The format used comes from the GEOSTAT initiative.

        Parameters:
            population_distribution_fp (str):Filepath of the data file to load (CSV)
            country_code (str):The country code to filter results for

        Returns:
            DensityMap object showing population density
        """

        # Load input data
        log.debug("Loading input data from %s...", population_distribution_fp)
        jrc = pd.read_csv(population_distribution_fp)

        # Filter this-country-only rows and augment with integer grid coords
        log.debug("Filtering for country with code %s...", country_code)
        jrc = jrc[jrc["CNTR_CODE"] == country_code]
        jrc['grid_x'] = pd.Series([int(x[9:13]) for x in jrc['GRD_ID']], index=jrc.index)
        jrc['grid_y'] = pd.Series([int(x[4:8]) for x in jrc['GRD_ID']], index=jrc.index)

        # These need converting to metres
        self.country_width  = 1000 * (jrc['grid_x'].max() - jrc['grid_x'].min() + 1)
        self.country_height = 1000 * (jrc['grid_y'].max() - jrc['grid_y'].min() + 1)
        log.info("Country with code %s has %ix%im of data", \
                 country_code, self.country_width, self.country_height)
        self.jrc = jrc


        self.prng                  = Random(random_seed)
        self.res_fact              = res_fact
        self.normalize             = normalize_interpolation
        self.shapefilename         = shapefilename
        self.shapefile_coordsystem = shapefile_coord_system

    def get_map(self) -> DensityMap:

        # Map the grid coordinates given onto a cartesian grid, each cell
        # of which represents the population density at that point
        log.debug("Building density matrix...")
        country = DensityMap(self.prng, (1000*self.jrc['grid_x'].min(),
                            1000*self.jrc['grid_y'].min()), self.country_width, self.country_height,
                            1000, shapefilename=self.shapefilename,
                            shapefile_coordsystem=self.shapefile_coordsystem)

        # Recompute the density index.  This _must_ be done with the above, and is an optimisation
        # to provide marginals for the normalisation/resampling op below
        for _, row in tqdm(self.jrc.iterrows(), total=self.jrc.shape[0]):

            # Read total population for this 1km chunk, \propto density
            location_density = row["TOT_P"]
            x                = row['grid_x'] - self.jrc['grid_x'].min()
            y                = row['grid_y'] - self.jrc['grid_y'].min()

            country.density[y][x] = location_density
        country.force_recompute_marginals()

        # Return the density, with linear interpolation or not
        if self.res_fact is not None:
            return country.resample(self.res_fact, self.normalize)
        return country
