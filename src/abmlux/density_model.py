"""Module for working with a population density map.

In ABMLUX population density maps are used to initialise locations with realistic distances
to one another, which in turn defines where people are located in space."""

import logging

import pandas as pd
from tqdm import tqdm

from abmlux.map import DensityMap

# Module log
log = logging.getLogger('density_model')

def read_density_model_jrc(filepath, country_code, res_fact, normalize, shapefilename,
                           shapefile_coordsystem):
    """Parse JRC-format country data and return a two-dimensional array
    containing population density weights per-kilometer.

    The format used comes from the GEOSTAT initiative.

    Parameters:
        filepath (str):Filepath of the data file to load (CSV)
        country_code (str):The country code to filter results for

    Returns:
        DensityMap object showing population density
    """

    # Load workbook
    log.debug("Loading input data from %s...", filepath)
    jrc = pd.read_csv(filepath)

    # Filter this-country-only rows and augment with integer grid coords
    log.debug("Filtering for country with code %s...", country_code)
    jrc = jrc[jrc["CNTR_CODE"] == country_code]
    jrc['grid_x'] = pd.Series([int(x[9:13]) for x in jrc['GRD_ID']], index=jrc.index)
    jrc['grid_y'] = pd.Series([int(x[4:8]) for x in jrc['GRD_ID']], index=jrc.index)

    # These need converting to metres
    country_width  = 1000 * (jrc['grid_x'].max() - jrc['grid_x'].min() + 1)
    country_height = 1000 * (jrc['grid_y'].max() - jrc['grid_y'].min() + 1)
    log.info("Country with code %s has %ix%im of data", country_code, country_width, country_height)

    # Map the grid coordinates given onto a cartesian grid, each cell
    # of which represents the population density at that point
    log.debug("Building density matrix...")
    country = DensityMap((1000*jrc['grid_x'].min(), 1000*jrc['grid_y'].min()),
                         country_width, country_height, 1000, shapefilename=shapefilename,
                         shapefile_coordsystem=shapefile_coordsystem)
    for _, row in tqdm(jrc.iterrows(), total=jrc.shape[0]):

        # Read total population for this 1km chunk, \propto density
        location_density = row["TOT_P"]
        x                = row['grid_x'] - jrc['grid_x'].min()
        y                = row['grid_y'] - jrc['grid_y'].min()

        country.density[y][x] = location_density
    country.force_recompute_marginals()

    # Return the density, with linear interpolation or not
    if res_fact is not None:
        return country.resample(res_fact, normalize)
    return country
