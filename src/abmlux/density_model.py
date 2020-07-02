#!/usr/bin/env python3

#DensityModel
#This file generates a population density matrix using data collected by the GEOSTAT initiative. Note
#that Luxembourg measures 57 km x 82 km.

import sys
import os.path as osp

import numpy as np
import pandas as pd
from tqdm import tqdm

from .config import Config


def build_density_model(config):

    # Load workbook
    print(f"Loading input data from {config.filepath('population_distribution_fp')}...")
    jrc = pd.read_csv(config.filepath('population_distribution_fp'))

    # Filter this-country-only rows and augment with integer grid coords
    print(f"Filtering for country with code {config['country_code']}...")
    jrc = jrc[jrc["CNTR_CODE"] == config['country_code']]
    jrc['grid_x'] = pd.Series([int(x[9:13]) for x in jrc['GRD_ID']], index=jrc.index)
    jrc['grid_y'] = pd.Series([int(x[4:8]) for x in jrc['GRD_ID']], index=jrc.index)

    country_width  = jrc['grid_x'].max() - jrc['grid_x'].min() + 1
    country_height = jrc['grid_y'].max() - jrc['grid_y'].min() + 1
    print(f"Country with code {config['country_code']} has {country_width}x{country_height}km of data")

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

