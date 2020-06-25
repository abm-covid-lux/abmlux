#!/usr/bin/env python3

#ABM5
#This file loads the agents, locations and network connections generated by the file NetworkModel, to
#gether with the intial distributions and transition matrices generated by the file MarkovModel, and
#simulates an epidemic. Note that the population size N is determined within the file NetworkModel. I
#n this file, one can set the length of the simulation in weeks and the number of initial seeds. Note
#that the simulation starts on a Sunday and follows the SEIRD framework.

import math
import random
import pickle

import numpy as np
import matplotlib.pyplot as plt
import xlsxwriter
from openpyxl import load_workbook
import pandas as pd
from tqdm import tqdm

import random_tools
from agent import Agent, AgentType, POPULATION_SLICES, HealthStatus
from location import Location
from config import load_config
import utils
from sim_time import SimClock
from activity import ActivityManager

NETWORK_INPUT_FILENAME    = "Network/Network.pickle"
INITIAL_DISTRIBUTIONS_FILENAME = "Initial_Distributions/initial.pickle"
TRANSITION_MATRIX_FILENAME     = "Transition_Matrices/transition_matrix.pickle"

PARAMETERS_FILENAME    = 'Data/simulation_parameters.yaml'

# ------------------------------------------------[ Config ]------------------------------------
print(f"Loading config from {PARAMETERS_FILENAME}...")
config           = load_config(PARAMETERS_FILENAME)
activity_manager = ActivityManager(config['activities'])
clock            = SimClock(config['tick_length_s'], config['simulation_length_days'])


# ------------------------------------------------[ Agents ]------------------------------------
print(f'Loading network data from {NETWORK_INPUT_FILENAME}...')
with open(NETWORK_INPUT_FILENAME, 'rb') as fin:
    network = pickle.load(fin)

locations_by_type = network['locations_by_type']
locations = utils.flatten(locations_by_type.values())
agents_by_type = network['agents_by_type']
agents = utils.flatten(agents_by_type.values())

utils.print_memory_usage()


# --------------------------------------[ Transition Matrices ]------------------------------------

print(f"Loading transition matrix from {TRANSITION_MATRIX_FILENAME}...")
with open(TRANSITION_MATRIX_FILENAME, 'rb') as fin:
    activity_transition_matrix = pickle.load(fin)
utils.print_memory_usage()


# ------------------------------------------------[ Locations ]------------------------------------
print('Loading pathogenic data...')

incubation_ticks = clock.days_to_ticks(config['incubation_period_days'])
infectious_ticks = clock.days_to_ticks(config['infectious_period_days'])

def get_p_death_func(p_death_config):
    """Return a function that takes an age and returns
    the absolute probability of death at the end of the
    infectious period"""

    # Make a slow lookup by checking the range.
    #
    # Assumes no overlapping ranges.
    def p_death_slow(age):
        for rng, p in p_death_config:
            if age >= rng[0] and age < rng[1]:
                return p
        return 0.0

    # Make a fast lookup. and use this for integers.
    # Fall through to the slow one if not in the list
    oldest_item = max([x[0][1] for x in p_death_config])
    fast_lookup = [p_death_slow(x) for x in range(0, oldest_item)]
    def p_death_fast(age):
        if age in fast_lookup:
            return fast_lookup[age]
        return p_death_slow(age)

    return p_death_fast

p_death = get_p_death_func(config['probability_of_death'])



# If two individuals, one susceptible and one infectious, spend ten minutes together in location j,
# then prob[j] is the average number of times, out of 10000 trials, that the susceptible will become
# infected:
p_transmit_by_location_type = {x: y for x, y in config['infection_probabilities_per_tick'].items()}



# ------------------------------------------[ Initial state ]------------------------------------
print('Simulating epidemic...')

# Infect a few people
for agent in random.sample(agents, k=config['initial_infections']):
    agent.health = HealthStatus.INFECTED




# Using the initial distribution individuals are now assigned starting locations:
print(f"Loading initial activity distributions from {INITIAL_DISTRIBUTIONS_FILENAME}...")
with open(INITIAL_DISTRIBUTIONS_FILENAME, 'rb') as fin:
    initial_activity_distributions = pickle.load(fin)

print(f"Seeding initial activity states and locations...")
for agent in agents:
    # allowed_locations = []
    # while len(allowed_locations) == 0:
    new_activity           = random_tools.multinoulli_dict(initial_activity_distributions[agent.agetyp])
    allowed_location_types = activity_manager.get_location_types(new_activity)
    allowed_locations      = agent.find_allowed_locations_by_type(allowed_location_types)

    if len(allowed_locations) == 0:
        print(f"Warning: No allowed locations found for agent {agent.inspect()} for activity {new_activity}"\
              f" (allowed location types={allowed_location_types})."\
              f"  Will resample from the starting distribution, but this is not ideal.")

    # Do this activity in this location
    agent.set_activity(new_activity, random.choice(list(allowed_locations)))



# ------------------------------------------------[ Simulate! ]------------------------------------
print(f"Simulating outbreak...")
# Finally the epidemic can be simulated. In each ten minute interval, the code first loops through all
# locations, in which the health status of individuals is updated, after which it loops through all 
# individuals, in which the locations of individuals are updated. Note that individuals only change 
# location if the Markov chain generates a new activity. For example, once an individual is inside a shop,
# they cannot move directly to another shop.

# For each agent, record where it is going next.  Entries are (HealthStatus, activity, location)
# 3-tuples, indexed by agent.
agent_health_state_change_time = {a: 0 for a in agents}
while t := clock.tick():
    next_agent_state = {}

    print(f"[{t} ticks] {clock.time_elapsed()} elapsed, {clock.time_remaining()} remaining")

    # Move people around the network
    time_in_week = int(t % clock.ticks_in_week) # How far through the week are we, in ticks?
    for agent in agents:

        # The dead don't participate
        if agent.health == HealthStatus.DEAD:
            continue

        # --- Risk infection of others at this location ---
        if agent.health == HealthStatus.INFECTED:
            # Small chance of passing to everyone else in the location who
            # is in the SUSCEPTIBLE state.
            location = agent.current_location
            susceptible_agents = [a for a in location.attendees
                                  if a.health == HealthStatus.SUSCEPTIBLE]
            for susceptible_agent in susceptible_agents:
                if random_tools.boolean(config['infection_probabilities_per_tick'][location.typ]):
                    next_agent_state[susceptible_agent] = (HealthStatus.EXPOSED, None, None)

        # --- Update health status ---
        if agent.health == HealthStatus.EXPOSED:
            # If we have incubated for long enough, become infected
            ticks_since_exposure = t - agent_health_state_change_time[agent]
            if ticks_since_exposure > incubation_ticks:
                next_agent_state[agent] = (HealthStatus.INFECTED, None, None)
        elif agent.health == HealthStatus.INFECTED:
            # If we have been infected for long enough, become uninfected (i.e.
            # dead or recovered)
            ticks_since_infection = t - agent_health_state_change_time[agent]
            if ticks_since_infection > infectious_ticks:
                # die or recover?
                if random_tools.boolean(p_death(agent.age)):
                    next_agent_state[agent] = (HealthStatus.DEAD, None, None)
                else:
                    next_agent_state[agent] = (HealthStatus.RECOVERED, None, None)

        # --- Update activity status ---
        weighted_next_activity_options = activity_transition_matrix[agent.agetyp][time_in_week][agent.current_activity]
        next_activity = random_tools.multinoulli_dict(weighted_next_activity_options)

        if next_activity != agent.current_activity:
            allowable_location_types = activity_manager.get_location_types(next_activity)
            allowable_locations      = agent.find_allowed_locations_by_type(allowable_location_types)
            next_location            = random.choice(list(allowable_locations))

            # Move to the activity, type selected
            # TODO: move the handling of merging tuples later
            next_agent_state[agent] = (next_agent_state[agent][0] if agent in next_agent_state else None,
                                       next_activity,
                                       next_location)



    # Update states according to markov chain
    # print(f"=> {len(next_agent_state)} state changes")
    for agent, transition in next_agent_state.items():

        next_health, next_activity, next_location = transition

        if next_health is not None:
            agent.next_health = next_health
        if next_activity is not None:
            agent.set_activity(next_activity, next_location)



import code; code.interact(local=locals())

# ------------------------------------------------[ Write output ]------------------------------------

print('Done.')
