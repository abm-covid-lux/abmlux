#!/usr/bin/env python3

#DensitySimulation

#This file simulates the random distribution of objects, according to the density matrix constructed
#in the file DensityModel.

import numpy as np
from openpyxl import load_workbook
import math
import random
import matplotlib.pyplot as plt

from tqdm import tqdm

from random_tools import multinoulli

random.seed(652)

DENSITY_MAP_FILENAME = 'Density_Map/Density_Map.csv'
OUTPUT_PLOT_FILENAME = 'Results/Density_map.png'
FIGURE_SIZE = (20, 20)
SAMPLE_SIZE = 1000

D = [[0 for x in range(57)] for y in range(82)] # FIXME: magic numbers
D = np.genfromtxt(DENSITY_MAP_FILENAME, delimiter=',', dtype = 'int')

ymarginals = []
for y in range(82):
    ymarginals.append(np.sum(np.array(D[y])))

print(f"Plotting to {OUTPUT_PLOT_FILENAME}...")
plt.figure(figsize=FIGURE_SIZE)
for s in tqdm(range(SAMPLE_SIZE)):
    ycoord = multinoulli(np.array(ymarginals))
    xcoord = multinoulli(np.array(D[ycoord]))
    plt.plot(xcoord,ycoord, marker = ".", color='green')

plt.savefig(OUTPUT_PLOT_FILENAME, dpi=100)
print('Done.')

