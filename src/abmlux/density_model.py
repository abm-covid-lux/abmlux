
import sys
import os.path as osp

import numpy as np
import pandas as pd
from tqdm import tqdm

from .config import Config



def read_density_model_jrc(filepath, country_code):
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
    print(f"Loading input data from {filepath}...")
    jrc = pd.read_csv(filepath)

    # Filter this-country-only rows and augment with integer grid coords
    print(f"Filtering for country with code {country_code}...")
    jrc = jrc[jrc["CNTR_CODE"] == country_code]
    jrc['grid_x'] = pd.Series([int(x[9:13]) for x in jrc['GRD_ID']], index=jrc.index)
    jrc['grid_y'] = pd.Series([int(x[4:8]) for x in jrc['GRD_ID']], index=jrc.index)

    country_width  = jrc['grid_x'].max() - jrc['grid_x'].min() + 1
    country_height = jrc['grid_y'].max() - jrc['grid_y'].min() + 1
    print(f"Country with code {country_code} has {country_width}x{country_height}km of data")

    # Map the grid coordinates given onto a cartesian grid, each cell
    # of which represents the population density at that point
    print(f"Building density matrix...")
    density = [[0 for x in range(country_width)] for y in range(country_height)]
    for i, row in tqdm(jrc.iterrows(), total=jrc.shape[0]):

        # Read total population for this 1km chunk, \propto density
        location_density = row["TOT_P"]
        x                = row['grid_x'] - jrc['grid_x'].min()
        y                = row['grid_y'] - jrc['grid_y'].min()

        density[y][x] = location_density

    # Return the density
    return density


