# ABMLUX
This is an agent-based model of COVID-19 in Luxembourg.


## Overview

### Input Data

Simulation parameters:
 * Total Population (N) --- in `NetworkModel`
 * Total Duration in weeks (T) --- in `ABM`

### Output Data

TBD

## Requirements

 * A recent python (TODO: what is this tested on?)
 * `pip install -r requirements.txt`


## Usage

 1. DensityModel
 2. NetworkModel
 3. MarkovModel
 4. DensitySimulation
 5. MarkovSimulation
 6. NetworkSimulation
 7. ABM



### 1. Construct Population Density Matrix
The file DensityModel constructs a population density matrix using Luxembourgish data.

### 2. Generate Agents and Locations
The file NetworkModel uses this matrix to procedurally generate a vitural representation of Luxembourg, consisting of agents and locations.

 Agents are assigned age and behaviour type (child, adult or retired) while locations are assigned coordinates and location type (house, school, restaurant etc). Agents are then matched to locations, determining precisely which locations they will be able to visit.

The behaviour of agents follows a time-inhomogeneous Markov chain and the initial distribution and transition matrices are constructed in the file MarkovModel.

### 3. Simulate
The files DensitySimulation, MarkovSimulation and NetworkSimulation (in that order) can be used to test the individual components.

The file ABM then simulates the epidemic, saving the results.



