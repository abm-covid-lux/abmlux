"""Module for working with a population density map.

In ABMLUX population density maps are used to initialise locations with realistic distances
to one another, which in turn defines where people are located in space."""

import logging

import numpy as np
import pandas as pd
from tqdm import tqdm
from scipy import interpolate

# Module log
log = logging.getLogger('density_model')

def distribution_interpolate(distribution, res_fact, normalize):
    """Returns an expanded distribution matrix, corresponding to a finer grid resolution, using
    linear interpolation.

    Parameters:
        distribution (numpy array):The distribution array returned from read_density_model_jrc
        res_fact (int):The factor by which the resolution is increased in a given dimension. This
                       should be an even integer, except if res_fact == 1 in which case the
                       original density is returned.
        normalize (boolean):If True then blocks of new squares are normalized to contain equal
                            populations as the original squares

    Returns:
        distribution_new(numpy array):An expanded distribution array of floats
    """

    if res_fact <= 0 or res_fact > 1000 or (res_fact % 2 != 0 and res_fact != 1) or \
                                        not isinstance(res_fact, int):
        raise ValueError("res_fact in distribution_interpolate must be a +ve even integer or 1")

    height, width = distribution.shape

    # Pad with a border of zeros
    padded_height = height + 2
    padded_width = width + 2

    padded_distribution = np.zeros((padded_height,padded_width))
    padded_distribution[1:height+1,1:width+1] = distribution

    # Map padded_density onto a grid within the unit square
    x = np.linspace(0, 1, num=padded_width, endpoint=True)
    y = np.linspace(0, 1, num=padded_height, endpoint=True)
    z = padded_distribution

    # Linearly interpolate
    interpolated_density = interpolate.interp2d(x, y, z)

    # The resolution of the grid is increased and interpolated vaules are assigned to each
    # new square
    x_indent = 1/((padded_width - 1)*res_fact*2)
    y_indent = 1/((padded_height - 1)*res_fact*2)

    x_new = np.linspace(x_indent, 1 - x_indent, num=(padded_width - 1)*res_fact, endpoint=True)
    y_new = np.linspace(y_indent, 1 - y_indent, num=(padded_height - 1)*res_fact, endpoint=True)

    half_res = int(res_fact/2)
    distribution_new = interpolated_density(x_new, y_new)[half_res:len(y_new) - half_res,
                                                          half_res:len(x_new) - half_res]
    
    if normalize == True:

        # Blocks of new squares are normalized to contain equal populations as the original
        # squares
        for i in range(width):
            for j in range(height):

                square = distribution_new[j*res_fact:(j+1)*res_fact, i*res_fact:(i+1)*res_fact]

                newsum = np.sum(square)
                oldsum = distribution[j][i]
                
                if newsum > 0:
                    square *= oldsum/newsum

    return distribution_new
    
def read_density_model_jrc(filepath, country_code, res_fact, normalize):
    """Parse JRC-format country data and return a two-dimensional array
    containing population density weights per-kilometer.

    The format used comes from the GEOSTAT initiative.

    Parameters:
        filepath (str):Filepath of the data file to load (CSV)
        country_code (str):The country code to filter results for

    Returns:
        density:km-by-km weights showing population density, indexed as [y][x]
    """

    # Load workbook
    log.debug("Loading input data from %s...", filepath)
    jrc = pd.read_csv(filepath)

    # Filter this-country-only rows and augment with integer grid coords
    log.debug("Filtering for country with code %s...", country_code)
    jrc = jrc[jrc["CNTR_CODE"] == country_code]
    jrc['grid_x'] = pd.Series([int(x[9:13]) for x in jrc['GRD_ID']], index=jrc.index)
    jrc['grid_y'] = pd.Series([int(x[4:8]) for x in jrc['GRD_ID']], index=jrc.index)

    country_width  = jrc['grid_x'].max() - jrc['grid_x'].min() + 1
    country_height = jrc['grid_y'].max() - jrc['grid_y'].min() + 1
    log.info("Country with code %s has %ix%ikm of data",
             country_code, country_width, country_height)

    # Map the grid coordinates given onto a cartesian grid, each cell
    # of which represents the population density at that point
    log.debug("Building density matrix...")
    density = [[0 for x in range(country_width)] for y in range(country_height)]
    for _, row in tqdm(jrc.iterrows(), total=jrc.shape[0]):

        # Read total population for this 1km chunk, \propto density
        location_density = row["TOT_P"]
        x                = row['grid_x'] - jrc['grid_x'].min()
        y                = row['grid_y'] - jrc['grid_y'].min()

        density[y][x] = location_density
    
    # Return the density, with linear interpolation or not
    if res_fact > 0 and res_fact <= 1000 and res_fact % 2 == 0:
        
        return distribution_interpolate(np.array(density), res_fact, normalize)
        
    else:
    
        return density