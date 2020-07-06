# ABMLUX
This is an agent-based model of COVID-19 in Luxembourg.


## Overview

### Input Data
Defined per-scenario in Scenarios/Name.  See the yaml config file for descriptions of each of the parameters.

## Requirements

 * python 3.8

## Usage

 * `pip install .`
 * `abmlux Scenarios/Luxembourg/config.yaml`



### 1. Construct Population Density Matrix
The file DensityModel constructs a population density matrix using Luxembourgish data.

### 2. Generate Agents and Locations
The file NetworkModel uses this matrix to procedurally generate a vitural representation of Luxembourg, consisting of agents and locations.

 Agents are assigned age and behaviour type (child, adult or retired) while locations are assigned coordinates and location type (house, school, restaurant etc). Agents are then matched to locations, determining precisely which locations they will be able to visit.

The behaviour of agents follows a time-inhomogeneous Markov chain and the initial distribution and transition matrices are constructed in the file MarkovModel.

### 3. Simulate
The files DensitySimulation, MarkovSimulation and NetworkSimulation (in that order) can be used to test the individual components.

The file ABM then simulates the epidemic, saving the results.



