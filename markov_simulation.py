#!/usr/bin/env python3

#Markov Simulation

#This file simulates the random movements of N individuals according to the dynamics constructed in t
#he file MarkovModel. In the example below, the simulation is performed for adults. The code can easi
#ly be adapted to instead simulate the behaviour of children or retired individuals. The simulation o
#ccurs over 1 week.

import numpy as np
import random
import xlsxwriter

from random_tools import multinoulli

random.seed(9001)

OUTPUT_FILENAME = 'Results/MarkovSimulation_Results.xlsx'
N = 1000 #Total population

Init_adult = [0 for i in range(14)]
Trans_adult = [[[0 for i in range(14)] for j in range(14)] for t in range(7*144)]

Init_adult = np.genfromtxt('Initial_Distributions/Init_adult.csv', delimiter=',', dtype = 'int')

for t in range(7*144):
    Trans_adult[t] = np.genfromtxt('Transition_Matrices/Trans_adult_' + str(t) + '.csv', delimiter=',', dtype = 'int')

#The trajectories of each individual will be recorded, descibing what individuals were doing duing ea
#ch ten minute interval of the simulation:

traj_adult = [[0 for i in range(N)] for t in range((T*7*144)+1)]

#The starting activity is randomized according to the intial distribution:

for i in range(N):
    traj_adult[0][i] = multinoulli(Init_adult)

#Subsequent activities are determined by the time-inhomogeneous Markov chain determined by the transi
#tion matrices:
t = 0
for t in range(7*144):
    for i in range(N):
        traj_adult[t+1][i] = multinoulli(Trans_adult[t][traj_adult[t][i],:])

#The results are saved:
workbook = xlsxwriter.Workbook(OUTPUT_FILENAME) 
worksheet = workbook.add_worksheet()

for i in range(14):
    for t in range(7*144):
        worksheet.write(t,i, traj_adult[t].count(i))

workbook.close() 

print('Done.')
