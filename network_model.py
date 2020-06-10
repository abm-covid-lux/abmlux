#!/usr/bin/env python3

#Network Model
#This file procedurally generates an environment, following Luxembourgish statistics.

import numpy as np
from openpyxl import load_workbook
import xlsxwriter
import math
import random
from tqdm import tqdm
import pandas as pd

from random_tools import multinoulli
from agent import Agent, AgentType
from location import Location

# Config
random.seed(652)        # FIXME: read from config
N                         = 1000 #Population size
AGE_DISTRIBUTION_FILENAME = 'Data/Age_Distribution.xlsx'
LOCATION_COUNT_FILENAME   = 'Data/Location_Counts.xlsx'
DENSITY_MAP_FILENAME      = 'Density_Map/Density_Map.csv'
MISC_PARAMETERS_FILENAME  = 'Data/Misc.xlsx'

AGENT_OUTPUT_FILENAME = 'Agents/Agents.xlsx'
LOCATION_OUTPUT_FILENAME = 'Locations/Locations.xlsx'

POPULATION_SLICES = {
        AgentType.CHILD: slice(None, 18),   # Children <18
        AgentType.ADULT: slice(18, 65),     # Adults 18-65
        AgentType.RETIRED: slice(65, None)  # Retired >65
    }

# ------------------------------------------------[ Agents ]------------------------------------
print('Initializing agents...')
ages = pd.read_excel(AGE_DISTRIBUTION_FILENAME)

# Extract useful series from input data
#
# NOTE: this makes the assumption that the ages run from 0-max without
#       any gaps.  TODO: check this on data load and throw errors
pop_by_age       = ages['population']
total_population = pop_by_age.sum()
pop_normalised   = pop_by_age / total_population

# How many agents per agent type
pop_by_agent_type = {atype: math.ceil(N * sum(pop_normalised[slce]))
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

# FIXME: Note that later on in the logic, agents are looked up by their offset in the 'agents' list
#        to infer their type.  They should use agents_by_type instead to prevent this fragile lookup.

# ------------------------------------------------[ Locations ]------------------------------------

print('Initializing locations...')
#A total of 13 locations are considered, as described in the file FormatLocations. The list is simila
#r to the list of activities, except the activity 'other house' does not require a separate listing a
#nd the location 'other work' refers to places of work not already listed as locations.

cntsworkbook = load_workbook(filename=LOCATION_COUNT_FILENAME)
cntssheet = cntsworkbook.active

Typdist = [0 for i in range(13)]

for i in range(13):
    Typdist[i] = math.ceil(int(cntssheet.cell(row=i+1, column=2).value)*(N/total_population)) #Total number of each location

M = sum(Typdist) #Total number of locations
L = [[0, [0,0]] for i in range(M)]
LocationList = [[] for j in range(13)]

#The total numbers of locations of each type are fixed deterministically:

i = 0
for j in range(13):
    while i < sum(Typdist[:j+1]):
        L[i] = Location(j,[0,0])
        LocationList[j].append(i)
        i = i + 1

#The density matrix contructed by the file DensityModel is now loaded:

density = np.genfromtxt(DENSITY_MAP_FILENAME, delimiter=',', dtype = 'int')

ymarginals = []

for y in range(82):
    ymarginals.append(np.sum(np.array(density[y])))

#Spatial coordinates are assigned according to the density matrix D. In particular, the 1 km x 1 km
#grid square is determined by randomizing with respect to D after which the precise location is ran
#domized uniformly within the grid square:

for j in range(13):
    for i in LocationList[j]:
        gridsquare_y = multinoulli(np.array(ymarginals))
        gridsquare_x = multinoulli(np.array(density[gridsquare_y]))
        y = random.randrange(1000)
        x = random.randrange(1000)
        L[i].coord = [(1000*gridsquare_x)+x,(1000*gridsquare_y)+y]

#Each house has one car in this model, and the coordinates of the cars are now reset to coincide wi
#th those of the houses:

for i in LocationList[5]:
    gridsquare_y = multinoulli(np.array(ymarginals))
    gridsquare_x = multinoulli(np.array(density[gridsquare_y]))
    y = random.randrange(1000)
    x = random.randrange(1000)
    L[i].coord = L[i - LocationList[5][0]].coord

print('Creating individualized location lists...')

#Each individual, for each activity, will now be assigned a list of possible locations at which the
#individual can perform that activity:

LocationListAgent = [[[] for j in range(14)] for i in range(N)]

#Some assignments will take into account distance:

maxsqdist = ((82*1000)**2)+((57*1000)**2)

sqdist = np.array([[maxsqdist for j in range(M)] for i in range(M)])

#The remaining code consists of three parts. First, the assignment of houses. Second, the assignmen
#t of other locations. Third, the saving of the data.





#--------Assigning houses--------
who = [[] for j in range(Typdist[0])] #A list of who lives in each house

#Assigning children according to Luxembourgish data:
miscworkbook = load_workbook(filename=MISC_PARAMETERS_FILENAME)
miscsheet = miscworkbook.active

c1 = miscsheet.cell(row=1, column=1).value
c2 = miscsheet.cell(row=2, column=1).value
c3 = miscsheet.cell(row=3, column=1).value

#Note that '3 or more children' will be considered '3 children' for simplicity.
n3 = math.floor(pop_by_agent_type[AgentType.CHILD]*c3/(c1+2*c2+3*c3)) #Number of houses with three children
n2 = math.floor(pop_by_agent_type[AgentType.CHILD]*c2/(c1+2*c2+3*c3)) #Number of houses with two children
n1 = pop_by_agent_type[AgentType.CHILD] - 2*n2 - 3*n3 #Number of houses with one child
ntot = n1 + n2 + n3 #Number of houses containing children

i = 0
for j in range(n3):
    LocationListAgent[i][0].append(j)
    who[j].append(i)
    LocationListAgent[i+1][0].append(j)
    who[j].append(i+1)
    LocationListAgent[i+2][0].append(j)
    who[j].append(i+2)
    i = i + 3
for j in range(n3,n3+n2):
    LocationListAgent[i][0].append(j)
    who[j].append(i)
    LocationListAgent[i+1][0].append(j)
    who[j].append(i+1)
    i = i + 2
j = n3+n2
for k in range(i,pop_by_agent_type[AgentType.CHILD]):
    LocationListAgent[k][0].append(j)
    who[j].append(i)
    j = j + 1

#Now adults are assigned to each house containing at least one child. The number of adults, which i
#s either 1 or 2, is determined randomly according to Luxembourgish data:
p1 = miscsheet.cell(row=5, column=1).value
p2 = miscsheet.cell(row=6, column=1).value

i = pop_by_agent_type[AgentType.CHILD]
for j in range(ntot):
    numberofadults = multinoulli(np.array([p1,p2]))
    if (numberofadults == 0):
        LocationListAgent[i][0].append(j)
        who[j].append(i)
        i = i + 1
    if (numberofadults == 1):
        LocationListAgent[i][0].append(j)
        who[j].append(i)
        LocationListAgent[i+1][0].append(j)
        who[j].append(i+1)
        i = i + 2

#Now all remaining individuals are randomly assigned to unoccupied houses, which it should be noted
#permits the possibility of empty houses;
for k in range(i,N):
    p = random.randrange(ntot,Typdist[0])
    LocationListAgent[k][0].append(p)
    who[p].append(k)

#--------Assigning other locations--------

#The assignment of individuals to workplaces is currently random. Note that the total list of work
#environments consists of the 'other work' locations plus all the other locations, except for house
#s, cars and the outdoors:
totalworklocations = []
for k in [1,2,3,6,7,8,9,10,11,12]:
    totalworklocations = totalworklocations + LocationList[k]

for i in range(N):
    LocationListAgent[i][1].append(totalworklocations[random.randrange(len(totalworklocations))])

#For each individual, a number of distinct homes, not including the individual's own home, are rand
#omly selected so that the individual is able to visit them:
maxtype = miscsheet.cell(row=8, column=1).value
for i in range(N):
    List = LocationList[0][:]
    List.remove(LocationListAgent[i][0][0])
    for j in range(min(maxtype,Typdist[0])):
        k = List[random.randrange(len(List))]
        LocationListAgent[i][13].append(k)
        List.remove(k)

#For each individual, a number of distinct restaurants, shops, units of public, cinemas or theatres
#and museums or zoos are randomly selected for the individual to visit or use:
for k in [3,6,7,11,12]:
    for i in range(N):
        List = LocationList[k][:]
        for j in range(min(maxtype,Typdist[k])):
            l = List[random.randrange(len(List))]
            LocationListAgent[i][k].append(l)
            List.remove(l)

#The following code assigns homes to locations in such a way that equal numbers of homes are assign
#ed to each location of a given type. For example, from the list of homes, a home is randomly selec
#ted and assigned to the nearest school, unless that school has already been assigned its share of
#homes, in which case the next nearest available school is assigned. This creates local spatial str
#ucture while ensuring that no school, for example, is assigned more homes than the other schools.
#This same procedure is also applied to medical locations, places of worship and indoor sport:

homesassigned = [0 for i in range(M)] #Number of homes assigned to each location

for k in [2,8,9,10]:
    for i in LocationList[0]:
        for j in LocationList[k]:
            sqdist[i][j] = (L[i].coord[0] - L[j].coord[0])**2 + (L[i].coord[1] - L[j].coord[1])**2
    List = LocationList[0][:]
    for l in range(Typdist[0]):
        i = List[random.randrange(len(List))]
        locationassigned = np.argmin(sqdist[i])
        for j in range(N):
            if (LocationListAgent[j][0][0] == i):
                LocationListAgent[j][k].append(locationassigned)
        homesassigned[locationassigned] = homesassigned[locationassigned] + 1
        if (homesassigned[locationassigned] >= max(math.ceil(Typdist[0]/Typdist[k]),1)):
            for m in LocationList[0]:
                sqdist[m][locationassigned] = maxsqdist
        List.remove(i)
    sqdist = np.array([ [ maxsqdist for j in range(M) ] for i in range(M)])

#The outdoors is treated as a single environment in which zero disease transmission will occur:
for i in range(N):
    LocationListAgent[i][4].append(LocationList[4][0])

#Each house is assigned a car:
for i in range(N):
    LocationListAgent[i][5].append(LocationList[5][LocationListAgent[i][0][0]])

#--------Save data--------
workbook = xlsxwriter.Workbook(AGENT_OUTPUT_FILENAME)
worksheet = workbook.add_worksheet()
for i in range(N):
    worksheet.write(i,0, i)
    worksheet.write(i,1, agents[i].agetyp)
    worksheet.write(i,2, agents[i].age)
    for k in range(14):
        worksheet.write(i,k+3,','.join(map(str, LocationListAgent[i][k])))

workbook.close()


workbook = xlsxwriter.Workbook(LOCATION_OUTPUT_FILENAME)
worksheet = workbook.add_worksheet()
for j in range(M):
    worksheet.write(j,0,j)
    worksheet.write(j,1,L[j].typ)
    worksheet.write(j,2,','.join(map(str, L[j].coord)))

workbook.close()

print('Done.')
