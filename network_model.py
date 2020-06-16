#!/usr/bin/env python3

#Network Model
#This file procedurally generates an environment, following Luxembourgish statistics.

import sys
import math
import random
import copy
from collections import defaultdict
import pickle

import numpy as np
from openpyxl import load_workbook
import xlsxwriter
from tqdm import tqdm
import pandas as pd
from scipy.spatial import KDTree

from random_tools import multinoulli, multinoulli_2d, multinoulli_dict
from agent import Agent, AgentType
from location import Location
from config import load_config

# Config
random.seed(652)        # FIXME: read from config
PICKLE_RECURSION_LIMIT = 10000  # Allows export of highly nested data
DENSITY_MAP_FILENAME   = 'Density_Map/Density_Map.csv'
PARAMETERS_FILENAME    = 'Data/network_parameters.yaml'

AGENT_OUTPUT_FILENAME    = "Agents/Agents.pickle"
LOCATION_OUTPUT_FILENAME = 'Locations/Locations.pickle'

POPULATION_SLICES = {
        AgentType.CHILD: slice(None, 18),   # Children <18
        AgentType.ADULT: slice(18, 65),     # Adults 18-65
        AgentType.RETIRED: slice(65, None)  # Retired >65
    }

# ------------------------------------------------[ Config ]------------------------------------
print(f"Loading config from {PARAMETERS_FILENAME}...")
config = load_config(PARAMETERS_FILENAME)

# ------------------------------------------------[ Agents ]------------------------------------
print('Initializing agents...')
# Extract useful series from input data
pop_by_age       = config['age_distribution']
pop_normalised   = [x / sum(pop_by_age) for x in pop_by_age]

# How many agents per agent type
pop_by_agent_type = {atype: math.ceil(config['n'] * sum(pop_normalised[slce]))
                     for atype, slce in POPULATION_SLICES.items()}
print(f"Agent count by type: {pop_by_agent_type}")

# The total numbers of children, adults and retired individuals are fixed deterministically, while the
# exact age of individuals within each group is determined randomly.
print(f"Constructing agents...")
agents = []
agents_by_type = {atype: [] for atype, _ in POPULATION_SLICES.items()}
for atype, slce in POPULATION_SLICES.items():
    print(f" - {atype.name}...")
    for i in tqdm(range(pop_by_agent_type[atype])):
        new_agent = Agent(atype, multinoulli(pop_by_age[slce]))
        agents.append(new_agent)
        agents_by_type[atype].append(new_agent)
        # print(f"-> {new_agent.inspect()}")

# FIXME: Note that later on in the logic, agents are looked up by their offset in the 'agents' list
#        to infer their type.  They should use agents_by_type instead to prevent this fragile lookup.
#
#        Unique agent assignments should be indexed by the UUIDs in the agent class





# ------------------------------------------------[ Locations ]------------------------------------

print('Initializing locations...')
#A total of 13 locations are considered, as described in the file FormatLocations. The list is simila
#r to the list of activities, except the activity 'other house' does not require a separate listing a
#nd the location 'other work' refers to places of work not already listed as locations.
location_counts = config['location_counts']
#location_count = sum(location_counts.values()) #Total number of locations
location_counts_normalised = {typ: x / sum(location_counts.values()) for typ, x in location_counts.items()}

# Adjust location counts by the ratio of the simulation size and real population size
location_counts = {typ: math.ceil((config['n'] / config['real_n']) * location_counts[typ])
                   for typ, x in location_counts.items()}
location_counts['Outdoor'] = 1

# Create locations for each type, of the amounts requested.
print(f"Creating location objects...")
locations = []
locations_by_type = {k: [] for k in location_counts.keys()}
for ltype, lcount in tqdm(location_counts.items()):
    new_locations = [Location(ltype, [0,0]) for _ in range(lcount)]
    locations_by_type[ltype] = new_locations
    locations += new_locations

# The density matrix contructed by the file DensityModel is now loaded:
print(f"Loading density matrix from {DENSITY_MAP_FILENAME}...")
density = np.genfromtxt(DENSITY_MAP_FILENAME, delimiter=',', dtype = 'int')
print(f"Density map is of size {density.shape}")


# Spatial coordinates are assigned according to the density matrix D. In particular, the 1 km x 1 km
# grid square is determined by randomizing with respect to D after which the precise location is
# randomized uniformly within the grid square:
#
# TODO: this should be done above, and there should be a clearer separate sampling function
#       to set the location as they are instantiated
print(f"Assigning coordinates to locations...")
marginals_cache = [sum(x) for x in density]
for location in tqdm(locations):
    grid_x, grid_y = multinoulli_2d(density, marginals_cache)
    location.set_coordinates((1000 * grid_x) + random.randrange(1000),
                             (1000 * grid_y) + random.randrange(1000))
del(marginals_cache)

# Each house has one car in this model, and the coordinates of the cars are now reset to coincide
# with those of the houses:
#
# TODO: this breaks if n(cars) != n(houses).  More robust allocation strategy needed
# TODO: this bit of code is very scenario-specific, it'd be good to separate it off
print(f"Assigning cars to houses...")
for car_location, house_location in zip(locations_by_type["Car"], locations_by_type["House"]):
    car_location.set_coordinates(house_location.coord)

print("Assigning locations to agents...")
# Each individual, for each activity, will now be assigned a list of possible locations at which the
# individual can perform that activity:
#  allowed_locations_by_agent = [[[] for j in range(14)] for i in range(config['n'])]


# ------- Assign Children ---------------
# Sample without replacement from both houses and
# child lists according to the weights above
#
# Note that these are taken IN ORDER because they have previously
# been assigned at random.  A possible extension is to shuffle
# these arrays to ensure random sampling even if the previous
# routines are not random.
print(f"Assigning children to houses...")
unclaimed_children = copy.copy(agents_by_type[AgentType.CHILD])
unassigned_houses  = copy.copy(locations_by_type['House'])

houses_with_children = set()
while len(unclaimed_children) > 0 and len(unassigned_houses) > 0:

    # Sample weighted by the aux data
    num_children = multinoulli_dict(config['children_per_house'])

    # Take from front of lists
    children = unclaimed_children[0:num_children]
    del(unclaimed_children[0:len(children)])
    house = unassigned_houses[0]
    del(unassigned_houses[0])

    # Allow children into the house,
    # and associate the children with the house
    for child in children:
        child.set_home(house)
        house.add_occupant(child)
    houses_with_children.add(house)



# ------- Assign Adults ---------------
# 1. Houses with children get one or two adults
#
print(f"Assigning adults to care for children...")
unassigned_adults = copy.copy(agents_by_type[AgentType.ADULT])
for house in tqdm(houses_with_children):
    if len(unassigned_adults) == 0:
        raise ValueError("Run out of adults to assign to child-containing households.  "
                         "There are too few adults to take care of children.")
    # Sample weighted by aux data
    num_adults = multinoulli_dict(config['adults_per_house_containing_children'])

    # Take from unassigned list
    adults = unassigned_adults[0:num_adults]
    del(unassigned_adults[0:num_adults])

    # Assign to house
    for adult in adults:
        adult.set_home(house)
        house.add_occupant(adult)

#
# 2. Remaining adults, and retired people,
#    get assigned to a random house.
#
# This brings with it the possibility of some households being large,
# and some houses remaining empty.
print(f"Assigning remaining adults/retired people...")
unassigned_agents = unassigned_adults + agents_by_type[AgentType.RETIRED]
for adult in tqdm(unassigned_adults):
    house = random.choice(locations_by_type["House"])

    adult.set_home(house)
    house.add_occupant(adult)


#--------Assigning other locations--------
#The assignment of individuals to workplaces is currently random. Note that the total list of work
#environments consists of the 'other work' locations plus all the other locations, except for house
#s, cars and the outdoors:

print(f"Assigning workplaces...")
for agent in tqdm(agents):
    location_type = multinoulli_dict(config['work_location_weights'])
    workplace = random.choice(locations_by_type[location_type])

    # This automatically allows the location
    agent.set_workplace(workplace)


# For each individual, a number of distinct homes, not including the individual's own home, are
# randomly selected so that the individual is able to visit them:
#
# TODO: assign exactly 10 houses
for agent in agents:
    num_new_houses = random.randrange(config['max_homes_allowed_to_visit'] - 1)

    # XXX: You will note this is random sampling with replacement.
    #      There's no issue with duplicates as we store them in a set, this simply means
    #      that we will select <= n items.
    new_houses = [random.choice(locations_by_type['House'])]

    agent.add_allowed_location(new_houses)

# For each individual, a number of distinct restaurants, shops, units of public, cinemas or theatres
# and museums or zoos are randomly selected for the individual to visit or use:
for agent in agents:
    num_entertainment = random.randrange(config['max_entertainment_allowed_to_visit'])
    location_types = [multinoulli_dict(config['entertainment_location_weights'])
                      for _ in range(num_entertainment)]
    new_entertainments = [random.choice(locations_by_type[t]) for t in location_types]

    agent.add_allowed_location(new_entertainments)





# --------------- Assign 'home assigned' locations ------------
# The following code assigns homes to locations in such a way that equal numbers of homes are
# assigned to each location of a given type. For example, from the list of homes, a home is
# randomly selected and assigned to the nearest school, unless that school has already been
# assigned its share of homes, in which case the next nearest available school is assigned.
# This creates local spatial structure while ensuring that no school, for example, is
# assigned more homes than the other schools. This same procedure is also applied to medical
# locations, places of worship and indoor sport:

max_homes_by_location_type = {
        lt: math.ceil(len(locations_by_type['House']) / len(locations_by_type[lt]))
        for lt in config['home_assignment_types']}

# Keep track of number of houses assigned to each location
for location_type in config['home_assignment_types']:

    print(f"Finding people to attend: {location_type}")
    kdtree = KDTree([loc.coord for loc in locations_by_type[location_type]])
    num_houses = defaultdict(int)

    # Traverse houses in random order
    shuffled_houses = copy.copy(locations_by_type['House'])
    random.shuffle(shuffled_houses)
    for house in tqdm(shuffled_houses):
        # Find the closest location of type location_type
        # and, if it's not full, assign every occupant
        # to the location

        knn = 2
        closest_locations = []
        while len(closest_locations) == 0:
            if (knn/2) > len(locations_by_type[location_type]):
                raise ValueError(f"Searching for more locations than exist for "
                                 f"type {location_type}.  This normally indicates"
                                 f"that all locations are full (which shouldn't happpen)")

            # Returns knn items, in order of nearness
            _, nearest_indices = kdtree.query(house.coord, knn)
            closest_locations = [locations_by_type[location_type][i] for i in nearest_indices
                                 if i < len(locations_by_type[location_type])]

            # Remove locations that have too many houses already
            closest_locations = [x for x in closest_locations if
                                 num_houses[x] < max_homes_by_location_type[location_type]]
            knn *= 2
        closest_location = closest_locations[0]

        # Add occupants to the location
        num_houses[closest_location] += 1
        for occupant in house.occupancy:
            occupant.add_allowed_location(closest_location)


#The outdoors is treated as a single environment in which zero disease transmission will occur:
if len(locations_by_type['Outdoor']) != 1:
    raise ValueError("More than one outdoor location found.  This shouldn't be.")
outdoors = locations_by_type['Outdoor'][0]
for agent in agents:
    agent.add_allowed_location(outdoors)

# Each house is assigned a car:
#
# FIXME: if num_houses != num_cars, this will fail.
for car, house in zip(locations_by_type["Car"], locations_by_type["House"]):
    for occupant in house.occupancy:
        occupant.add_allowed_location(car)


#--------Save data--------
sys.setrecursionlimit(PICKLE_RECURSION_LIMIT)
print(f"Writing agents list to {AGENT_OUTPUT_FILENAME}...")
with open(AGENT_OUTPUT_FILENAME, 'wb') as fout:
    pickle.dump(agents_by_type, fout)
print(f"Writing locations list to {LOCATION_OUTPUT_FILENAME}...")
with open(LOCATION_OUTPUT_FILENAME, 'wb') as fout:
    pickle.dump(locations_by_type, fout)

print('Done.')
