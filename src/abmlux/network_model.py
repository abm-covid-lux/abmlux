"""This file procedurally generates an environment, following Luxembourgish statistics."""

import math
import copy
from collections import defaultdict
import logging

from tqdm import tqdm
from scipy.spatial import KDTree

from .random_tools import (multinoulli, multinoulli_dict, random_randrange,
                           random_sample, random_choice, random_shuffle)
from .agent import Agent, AgentType, POPULATION_SLICES, HealthStatus
from .location import Location
from .activity_manager import ActivityManager
from .network import Network
from .sim_time import SimClock


log = logging.getLogger('network_model')

def create_locations(network, density_map, config):
    """Create a number of Location objects within the network, according to the density map
    given and the distributions defined in the config."""

    log.debug('Initializing locations...')

    location_counts = config['location_counts']

    # Adjust location counts by the ratio of the simulation size and real population size
    location_counts = {typ: math.ceil((config['n'] / config['real_n']) * location_counts[typ])
                       for typ, x in location_counts.items()}
    location_counts['Outdoor'] = 1

    # Create locations for each type, of the amounts requested.
    log.debug("Creating location objects...")
    for ltype, lcount in tqdm(location_counts.items()):
        for _ in range(lcount):

            new_coord = density_map.sample_coord()

            # Add location to the network
            new_location = Location(ltype, new_coord)
            network.add_location(new_location)



def create_agents(network, config):
    """Creaye a number of Agent objects within the network, according to the distributions
    specified in the configuration object provided."""

    log.debug('Initializing agents...')
    # Extract useful series from input data
    pop_by_age       = config['age_distribution']
    pop_normalised   = [x / sum(pop_by_age) for x in pop_by_age]

    # How many agents per agent type
    pop_by_agent_type = {atype: math.ceil(config['n'] * sum(pop_normalised[slce]))
                         for atype, slce in POPULATION_SLICES.items()}
    log.info("Agent count by type: %s", pop_by_agent_type)

    # The total numbers of children, adults and retired individuals are fixed deterministically,
    # while the exact age of individuals within each group is determined randomly.
    log.debug("Constructing agents...")
    for atype, slce in POPULATION_SLICES.items():
        log.debug(" - %s...", atype.name)
        for _ in tqdm(range(pop_by_agent_type[atype])):

            # Sample a point from the age distribution within this slice
            age = (slce.start or 0) + multinoulli(pop_by_age[slce])

            new_agent = Agent(atype, age)
            network.add_agent(new_agent)






def assign_homes(network, config, activity_manager, home_activity_type):
    """Define home locations for each agent"""
    # pylint: disable=too-many-locals

    # ------- Assign Children ---------------
    # Sample without replacement from both houses and
    # child lists according to the weights above
    #
    # Note that these are taken IN ORDER because they have previously been assigned at random.
    # A possible extension is to shuffle these arrays to ensure random sampling even if the
    # previous routines are not random.
    log.debug("Assigning children to houses...")

    # Look up all locations where agents can perform the activity representing being in a home
    unassigned_houses  = network.locations_for_types(activity_manager.get_location_types(home_activity_type))
    unclaimed_children = copy.copy(network.agents_by_type[AgentType.CHILD])
    log.debug("%i unassigned houses, %i unassigned children",
              len(unassigned_houses), len(unclaimed_children))

    houses_with_children = set()
    occupancy            = {l: [] for l in unassigned_houses}
    while len(unclaimed_children) > 0 and len(unassigned_houses) > 0:

        # Sample weighted by the aux data
        num_children = multinoulli_dict(config['children_per_house'])

        # Take from front of lists
        children = unclaimed_children[0:num_children]
        del unclaimed_children[0:len(children)]
        house = unassigned_houses[0]
        del unassigned_houses[0]

        # Allow children into the house,
        # and associate the children with the house
        for child in children:
            child.add_activity_location(activity_manager.as_int(home_activity_type), house)
            occupancy[house].append(child)
        houses_with_children.add(house)
    log.debug("%i houses have >=1 children.  %i houses have no occupants yet",
              len(houses_with_children), len(unassigned_houses))

    # ------- Assign Adults ---------------
    # 1. Houses with children get one or two adults
    #
    unassigned_adults = copy.copy(network.agents_by_type[AgentType.ADULT])
    log.debug("Assigning adults to care for children (%i adults available)...",
              len(unassigned_adults))
    for house in tqdm(houses_with_children):
        if len(unassigned_adults) == 0:
            raise ValueError("Run out of adults to assign to child-containing households.  "
                             "There are too few adults to take care of children.")
        # Sample weighted by aux data
        num_adults = multinoulli_dict(config['adults_per_house_containing_children'])

        # Take from unassigned list
        adults = unassigned_adults[0:num_adults]
        del unassigned_adults[0:num_adults]

        # Assign to house
        for adult in adults:
            adult.add_activity_location(activity_manager.as_int(home_activity_type), house)
            occupancy[house].append(adult)

    #
    # 2. Remaining adults, and retired people,
    #    get assigned to a random house.
    #
    # This brings with it the possibility of some households being large,
    # and some houses remaining empty.
    log.debug("Assigning %i adults and %i retired people to %i houses...",
              len(unassigned_adults), len(network.agents_by_type[AgentType.RETIRED]),
              len(unassigned_houses))
    unassigned_agents = unassigned_adults + network.agents_by_type[AgentType.RETIRED]
    houses  = network.locations_for_types(activity_manager.get_location_types(home_activity_type))
    for adult in tqdm(unassigned_agents):
        house = random_choice(houses)
        adult.add_activity_location(activity_manager.as_int(home_activity_type), house)
        occupancy[house].append(adult)

    return occupancy


def assign_workplaces(network, activity_manager, work_activity_type):
    """Assign a place of work for each agent."""

    # The assignment of individuals to workplaces

    log.debug("Assigning workplaces...")
    for agent in tqdm(network.agents):
        location_type = random_choice(activity_manager.get_location_types(work_activity_type))
        workplace = random_choice(network.locations_by_type[location_type])

        # This automatically allows the location
        agent.add_activity_location(activity_manager.as_int(work_activity_type), workplace)


def assign_other_houses(network, config, activity_manager, home_activity_type,
                        other_house_activity_type):
    """Assign other houses agents may visit"""
    # For each individual, a number of distinct homes, not including the individual's own home, are
    # randomly selected so that the individual is able to visit them:
    log.info("Assigning other houses agents may visit...")
    houses = network.locations_for_types(activity_manager.get_location_types(other_house_activity_type))
    for agent in tqdm(network.agents):
        # This may select n-1 if the agent's current home is in the samole
        houses_to_visit = random_sample(houses, k=config['homes_allowed_to_visit'])

        # Blacklist the agent's own home
        houses_to_visit = [h for h in houses_to_visit
                           if h not in agent.activity_locations[activity_manager.as_int(home_activity_type)]]

        agent.add_activity_location(activity_manager.as_int(other_house_activity_type),
                                    houses_to_visit)


def assign_entertainment_venues(network, config, activity_manager, entertainment_activity_type):
    """Assign some entertainment venues for agents to visit"""
    # For each agent, a number of distinct entertainment venues are randomly selected.
    # First we ensure there is one of each
    log.info("Assigning entertainment venues: %s...", entertainment_activity_type)
    venues = network.locations_for_types(activity_manager.get_location_types(entertainment_activity_type))
    for agent in tqdm(network.agents):
        num_locations      = max(1, random_randrange(config['max_entertainment_allowed_to_visit']))
        new_entertainments = random_sample(venues, k=min(len(venues), num_locations))

        agent.add_activity_location(activity_manager.as_int(entertainment_activity_type),
                                    new_entertainments)


def assign_householders_by_proximity(network, activity_manager, occupancy, activity_type):
    """For the location type given, select nearby houses and assign all occupants to
    attend this location.  If the location is full, move to the next nearby location, etc."""

    log.info("Assigning proximate locations for activity %s...", activity_type)

    # The following code assigns homes to locations in such a way that equal numbers of homes are
    # assigned to each location of a given type. For example, from the list of homes, a home is
    # randomly selected and assigned to the nearest school, unless that school has already been
    # assigned its share of homes, in which case the next nearest available school is assigned.
    # This creates local spatial structure while ensuring that no school, for example, is
    # assigned more homes than the other schools. This same procedure is also applied to medical
    # locations, places of worship and indoor sport:
    log.debug("Finding people to perform activity: %s", activity_type)
    log.debug("Location types: %s", activity_manager.get_location_types(activity_type))

    # Ensure we have at least one location of this type
    locations = network.locations_for_types(activity_manager.get_location_types(activity_type))
    log.debug("Found %i available locations", len(locations))
    assert len(locations) > 0

    max_homes  = math.ceil(network.count('House') / len(locations))
    kdtree     = KDTree([l.coord for l in locations])
    num_houses = defaultdict(int)

    # Traverse houses in random order
    shuffled_houses = copy.copy(network.locations_by_type['House'])
    random_shuffle(shuffled_houses)
    for house in tqdm(shuffled_houses):
        # Find the closest location and, if it's not full, assign every occupant to the location

        knn = 2
        closest_locations = []
        while len(closest_locations) == 0:
            if (knn/2) > len(locations):
                raise ValueError(f"Searching for more locations than exist for "
                                 f"types {activity_manager.get_location_types(activity_type)}.  "
                                 f"This normally indicates that all locations are full.")

            # Returns knn items, in order of nearness
            _, nearest_indices = kdtree.query(house.coord, knn)
            closest_locations = [locations[i] for i in nearest_indices if i < len(locations)]

            # Remove locations that have too many houses already
            closest_locations = [x for x in closest_locations if num_houses[x] < max_homes]
            knn *= 2
        closest_location = closest_locations[0]

        # Add all occupants of this house to the location
        num_houses[closest_location] += 1

        for occupant in occupancy[house]:
            occupant.add_activity_location(activity_manager.as_int(activity_type), closest_location)


def assign_outdoors(network, activity_manager, outdoor_activity_type):
    """Ensure everyone is allowed to access the outdoors"""

    outdoor_locations = network.locations_for_types(activity_manager.get_location_types(outdoor_activity_type))

    #The outdoors is treated as a single environment in which zero disease transmission will occur:
    if len(outdoor_locations) != 1:
        raise ValueError("More than one outdoor location found.  This shouldn't be.")

    for agent in network.agents:
        agent.add_activity_location(activity_manager.as_int(outdoor_activity_type),
                                    outdoor_locations[0])


def assign_cars(network, activity_manager, occupancy, car_activity_type):
    """Assign cars to houses.  This means updating the location to match
    the house, and ensuring all occupants at the house see the "car" activity
    as using that particular car"""

    houses = network.locations_by_type["House"]
    cars = network.locations_by_type["Car"]
    log.debug("Assigning %i cars to %i houses...", len(cars), len(houses))

    assert len(houses) == len(cars)

    # Each house is assigned a car:
    for car, house in tqdm(list(zip(cars, houses))):
        car.set_coordinates(house.coord)

        for occupant in occupancy[house]:
            occupant.add_activity_location(activity_manager.as_int(car_activity_type), car)


def build_network_model(config, density_map):
    """Create agents and locations according to the population density map given"""

    activity_manager = ActivityManager(config['activities'])

    # Create and populate the network
    log.info("Creating network")
    network = Network(density_map)
    create_agents(network, config)
    create_locations(network, density_map, config)

    log.info("Assigning locations to agents...")
    occupancy = assign_homes(network, config, activity_manager, "House")
    assign_workplaces(network, activity_manager, "Work")
    assign_other_houses(network, config, activity_manager, "House", "Other House")

    for entertainment_activity_type in config['entertainment_activities']:
        assign_entertainment_venues(network, config, activity_manager, entertainment_activity_type)

    for activity_type in config['whole_household_activities']:
        assign_householders_by_proximity(network, activity_manager, occupancy, activity_type)

    assign_outdoors(network, activity_manager, "Outdoor")
    assign_cars(network, activity_manager, occupancy, "Car")

    return network




def assign_activities(config, network, activity_distributions):
    """Assign activities and locations to agents according to the distributions provided."""

    clock = SimClock(config['tick_length_s'], config['simulation_length_days'], config['epoch'])

    # ------------------------------------------[ Initial state ]-----------------------------------
    log.debug("Loading initial state for simulation...")
    # Infect a few people
    for agent in random_sample(network.agents, k=config['initial_infections']):
        agent.health = HealthStatus.INFECTED

    log.debug("Seeding initial activity states and locations...")
    for agent in network.agents:

        # Get distribution for this type at the starting time step
        distribution = activity_distributions[agent.agetyp][clock.epoch_week_offset]
        assert sum(distribution.values()) > 0
        new_activity      = multinoulli_dict(distribution)
        allowed_locations = agent.locations_for_activity(new_activity)

        # Warning: No allowed locations found for agent {agent.inspect()} for activity new_activity
        assert len(allowed_locations) >= 0

        new_location = random_choice(list(allowed_locations))

        # Do this activity in a random location
        agent.set_activity(new_activity, new_location)

    return network
