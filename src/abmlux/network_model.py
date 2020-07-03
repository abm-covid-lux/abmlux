#!/usr/bin/env python3

#Network Model
#This file procedurally generates an environment, following Luxembourgish statistics.

import os.path as osp
import sys
import math
import random
import copy
from collections import defaultdict
import pickle
import logging

import numpy as np
from tqdm import tqdm
import pandas as pd
from scipy.spatial import KDTree

from .random_tools import multinoulli, multinoulli_2d, multinoulli_dict
from .agent import Agent, AgentType, POPULATION_SLICES
from .location import Location
from .activity import ActivityManager
from .network import Network



log = logging.getLogger('network_model')





def create_locations(network, density, config):

    log.debug('Initializing locations...')
    # A total of 13 locations are considered, as described in the file FormatLocations. The list is
    # similar to the list of activities, except the activity 'other house' does not require a separate
    # listing and the location 'other work' refers to places of work not already listed as locations.
    location_counts = config['location_counts']
    location_counts_normalised = {typ: x / sum(location_counts.values()) for typ, x in location_counts.items()}

    # Adjust location counts by the ratio of the simulation size and real population size
    location_counts = {typ: math.ceil((config['n'] / config['real_n']) * location_counts[typ])
                       for typ, x in location_counts.items()}
    location_counts['Outdoor'] = 1

    # Create locations for each type, of the amounts requested.
    log.debug(f"Creating location objects...")
    marginals_cache = [sum(x) for x in density]
    for ltype, lcount in tqdm(location_counts.items()):
        for _ in range(lcount):

            # Sample a point from the density map
            grid_x, grid_y = multinoulli_2d(density, marginals_cache)
            x, y = (1000 * grid_x) + random.randrange(1000), (1000 * grid_y) + random.randrange(1000)

            # Add location to the network
            new_location = Location(ltype, (x, y))
            network.add_location(new_location)



def create_agents(network, config):
    log.debug('Initializing agents...')
    # Extract useful series from input data
    pop_by_age       = config['age_distribution']
    pop_normalised   = [x / sum(pop_by_age) for x in pop_by_age]

    # How many agents per agent type
    pop_by_agent_type = {atype: math.ceil(config['n'] * sum(pop_normalised[slce]))
                         for atype, slce in POPULATION_SLICES.items()}
    log.info(f"Agent count by type: {pop_by_agent_type}")

    # The total numbers of children, adults and retired individuals are fixed deterministically, while the
    # exact age of individuals within each group is determined randomly.
    log.debug(f"Constructing agents...")
    for atype, slce in POPULATION_SLICES.items():
        log.debug(f" - {atype.name}...")
        for i in tqdm(range(pop_by_agent_type[atype])):

            # Sample a point from the age distribution within this slice
            age = (slce.start or 0) + multinoulli(pop_by_age[slce])

            new_agent = Agent(atype, age)
            network.add_agent(new_agent)






def assign_homes(network, config):
    """Define home locations for each agent"""


    # ------- Assign Children ---------------
    # Sample without replacement from both houses and
    # child lists according to the weights above
    #
    # Note that these are taken IN ORDER because they have previously
    # been assigned at random.  A possible extension is to shuffle
    # these arrays to ensure random sampling even if the previous
    # routines are not random.
    #
    # FIXME: this is a dumb way of doing it.
    log.debug(f"Assigning children to houses...")
    unclaimed_children = copy.copy(network.agents_by_type[AgentType.CHILD])
    unassigned_houses  = copy.copy(network.locations_by_type['House'])

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
        houses_with_children.add(house)


    # ------- Assign Adults ---------------
    # 1. Houses with children get one or two adults
    #
    log.debug(f"Assigning adults to care for children...")
    unassigned_adults = copy.copy(network.agents_by_type[AgentType.ADULT])
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

    #
    # 2. Remaining adults, and retired people,
    #    get assigned to a random house.
    #
    # This brings with it the possibility of some households being large,
    # and some houses remaining empty.
    log.debug(f"Assigning remaining adults/retired people...")
    unassigned_agents = unassigned_adults + network.agents_by_type[AgentType.RETIRED]
    for adult in tqdm(unassigned_agents):
        house = random.choice(network.locations_by_type["House"])

        adult.set_home(house)





def assign_workplaces(network, config, activity_manager):
    """Assign a place of work for each agent."""

    # The assignment of individuals to workplaces is currently random.
    # Note that the total list of work environments consists of the 'other work' locations plus all the 
    # other locations, except for houses, cars and the outdoors:
    log.debug(f"Assigning workplaces...")
    for agent in tqdm(network.agents):
        location_type = random.choice(activity_manager.get_location_types("Work"))
        workplace = random.choice(network.locations_by_type[location_type])

        # This automatically allows the location
        agent.set_workplace(workplace)



def assign_other_houses(network, config):
    """Assign other houses agents may visit"""
    # For each individual, a number of distinct homes, not including the individual's own home, are
    # randomly selected so that the individual is able to visit them:
    #
    # TODO: assign exactly 10 houses
    for agent in tqdm(network.agents):
        # This may select n-1 if the agent's current home is in the samole
        new_houses = random.sample(network.locations_by_type['House'], k=config['homes_allowed_to_visit'])

        agent.add_allowed_location(new_houses)



def assign_entertainment_venues(network, config):
    """Assign some entertainment venues for agents to visit"""
    # For each agent, a number of distinct entertainment venues are randomly selected.
    # First we ensure there is one of each
    for agent in tqdm(network.agents):
        for location_type in config['entertainment_locations']:
            num_locations      = max(1, random.randrange(config['max_entertainment_allowed_to_visit']))
            new_entertainments = random.sample(network.locations_by_type[location_type],\
                                               k=min(len(network.locations_by_type[location_type]), num_locations))

            agent.add_allowed_location(new_entertainments)




def assign_householders_by_proximity(network, config, activity_manager, location_type):
    """For the location type given, select nearby houses and assign all occupants to
    attend this location.  If the location is full, move to the next nearby location, etc."""

    # The following code assigns homes to locations in such a way that equal numbers of homes are
    # assigned to each location of a given type. For example, from the list of homes, a home is
    # randomly selected and assigned to the nearest school, unless that school has already been
    # assigned its share of homes, in which case the next nearest available school is assigned.
    # This creates local spatial structure while ensuring that no school, for example, is
    # assigned more homes than the other schools. This same procedure is also applied to medical
    # locations, places of worship and indoor sport:
    log.debug(f"Finding people to attend: {location_type}")

    # Ensure we have at least one location of this type
    assert(network.count(location_type) > 0)

    max_homes  = math.ceil(network.count('House') / network.count(location_type))
    kdtree     = KDTree([loc.coord for loc in network.locations_by_type[location_type]])
    num_houses = defaultdict(int)

    # Traverse houses in random order
    shuffled_houses = copy.copy(network.locations_by_type['House'])
    random.shuffle(shuffled_houses)
    for house in tqdm(shuffled_houses):
        # Find the closest location of type location_type
        # and, if it's not full, assign every occupant
        # to the location

        knn = 2
        closest_locations = []
        while len(closest_locations) == 0:
            if (knn/2) > network.count(location_type):
                raise ValueError(f"Searching for more locations than exist for "
                                 f"type {location_type}.  This normally indicates"
                                 f"that all locations are full (which shouldn't happpen)")

            # Returns knn items, in order of nearness
            _, nearest_indices = kdtree.query(house.coord, knn)
            closest_locations = [network.locations_by_type[location_type][i] for i in nearest_indices
                                 if i < network.count(location_type)]

            # Remove locations that have too many houses already
            closest_locations = [x for x in closest_locations if num_houses[x] < max_homes]
            knn *= 2
        closest_location = closest_locations[0]

        # Add occupants to the location
        num_houses[closest_location] += 1
        for occupant in house.occupancy:
            occupant.add_allowed_location(closest_location)


def assign_outdoors(network, config):
    #The outdoors is treated as a single environment in which zero disease transmission will occur:
    if len(network.locations_by_type['Outdoor']) != 1:
        raise ValueError("More than one outdoor location found.  This shouldn't be.")
    outdoors = network.locations_by_type['Outdoor'][0]
    for agent in network.agents:
        agent.add_allowed_location(outdoors)


def assign_cars(network, config):
    # Each house is assigned a car:
    #
    # FIXME: if num_houses != num_cars, this will fail.
    for car, house in zip(network.locations_by_type["Car"], network.locations_by_type["House"]):
        car.set_coordinates(house.coord)
        for occupant in house.occupancy:
            occupant.add_allowed_location(car)


def build_network_model(config, density):

    activity_manager = ActivityManager(config['activities'])

    # Create and populate the network
    log.info("Creating network")
    network = Network()
    create_agents(network, config)
    create_locations(network, density, config)

    log.info("Assigning locations to agents...")

    assign_homes(network, config)
    assign_workplaces(network, config, activity_manager)
    assign_other_houses(network, config)
    assign_entertainment_venues(network, config)

    for location_type in config['home_assignment_types']:
        assign_householders_by_proximity(network, config, activity_manager, location_type)

    assign_outdoors(network, config)
    assign_cars(network, config)

    return network

