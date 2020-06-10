#!/use/bin/env python3

#DensityModel

#This file generates a population density matrix using data collected by the GEOSTAT initiative. Note
#that Luxembourg measures 57 km x 82 km.

import math

import numpy as np
import pandas as pd
from tqdm import tqdm

# Config
INPUT_FILENAME = 'Data/JRC.xlsx'
OUTPUT_FILENAME = 'Density_Map/Density_Map.csv'
COORD_OFFSET = (4014, 2934)
LUXEMBOURG_SIZE_KM = (57, 82)   # width, height
LUXEMBOURG_COUNTRY_CODE = "LU"

def parse_coordinates(coord_string, x_offset=0, y_offset=0):
    """Parses a location (what format?),

    returning X, Y coordinates within the space given.

    e.g. 1kmN1621E6359"""

    x = int(coord_string[9:13]) - x_offset
    y = int(coord_string[4:8]) - y_offset

    return x, y


# Load workbook
print(f"Loading input data from {INPUT_FILENAME}...")
#wgtworkbook = load_workbook(filename=INPUT_FILENAME)
#wgtsheet = wgtworkbook.active
jrc = pd.read_excel(INPUT_FILENAME)

# Filter luxembourg-only rows
jrc = jrc[jrc["CNTR_CODE"] == LUXEMBOURG_COUNTRY_CODE]

# Iterate over each 1kmx1km location in the input data, reading
# the location and population density for each.
density = [[0 for x in range(LUXEMBOURG_SIZE_KM[0])]
                for y in range(LUXEMBOURG_SIZE_KM[1])]
for i, row in tqdm(jrc.iterrows(), total=jrc.shape[0]):

    # Read total population for this 1km chunk, \propto density
    location_density = row["TOT_P"]
    x, y             = parse_coordinates(row["GRD_ID"], COORD_OFFSET[0], COORD_OFFSET[1])

    density[y][x] = location_density

print(f"Saving output to {OUTPUT_FILENAME}...")
np.savetxt(OUTPUT_FILENAME, density, fmt='%i', delimiter=',')
print('Done.') 
