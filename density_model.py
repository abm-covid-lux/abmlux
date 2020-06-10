#!/use/bin/env python3

#DensityModel
#This file generates a population density matrix using data collected by the GEOSTAT initiative. Note
#that Luxembourg measures 57 km x 82 km.

import numpy as np
import pandas as pd
from tqdm import tqdm

# Config
INPUT_FILENAME  = 'Data/JRC.xlsx'
OUTPUT_FILENAME = 'Density_Map/Density_Map.csv'
COUNTRY_CODE    = "LU"

# Load workbook
print(f"Loading input data from {INPUT_FILENAME}...")
jrc = pd.read_excel(INPUT_FILENAME)

# Filter this-country-only rows and augment with integer grid coords
print(f"Filtering for country with code {COUNTRY_CODE}...")
jrc = jrc[jrc["CNTR_CODE"] == COUNTRY_CODE]
jrc['grid_x'] = pd.Series([int(x[9:13]) for x in jrc['GRD_ID']], index=jrc.index)
jrc['grid_y'] = pd.Series([int(x[4:8]) for x in jrc['GRD_ID']], index=jrc.index)

country_width  = jrc['grid_x'].max() - jrc['grid_x'].min() + 1
country_height = jrc['grid_y'].max() - jrc['grid_y'].min() + 1
print(f"Country with code {COUNTRY_CODE} has {country_width}x{country_height}km of data")

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

print(f"Saving output to {OUTPUT_FILENAME}...")
np.savetxt(OUTPUT_FILENAME, density, fmt='%i', delimiter=',')
print('Done.')
