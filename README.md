This is an agent-based model of COVID-19 in Luxembourg.



The file DensityModel constructs a population density matrix using Luxembourgish data.

The file NetworkModel uses this matrix to procedurally generate a vitural representation of Luxembourg, consisting of agents and locations.

 Agents are assigned age and behaviour type (child, adult or retired) while locations are assigned coordinates and location type (house, school, restaurant etc). Agents are then matched to locations, determining precisely which locations they will be able to visit.



The behaviour of agents follows a time-inhomogeneous Markov chain and the initial distribution and transition matrices are constructed in the file MarkovModel.



The files DensitySimulation, NetworkSimulation and MarkovSimulation can be used to test the individual components.



The file ABM then simulates the epidemic, saving the results.



Note that the total population N is specified in the file NetworkModel while the total duration of the simulation in weeks T is specified in the file ABM.