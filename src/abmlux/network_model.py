"""This file procedurally generates an environment, following Luxembourgish statistics."""

import math
import copy
from collections import defaultdict
import logging

from tqdm import tqdm
from scipy.spatial import KDTree

from .random_tools import (multinoulli, multinoulli_dict, random_randrange,
                           random_sample, random_choice, random_shuffle, random_randrange_interval)
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
    random_location_counts = config['random_location_counts']

    # Adjust location counts by the ratio of the simulation size and real population size
    location_counts = {typ: math.ceil((config['n'] / config['real_n']) * location_counts[typ])
                       for typ, x in location_counts.items()}
    location_counts['Outdoor'] = 1

    # Create locations for each type, of the amounts requested.
    log.info("Creating location objects...")
    for ltype, lcount in tqdm(location_counts.items()):
        if ltype not in random_location_counts:
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
    # Add an appropriate number of cross border workers as adults
    pop_by_border_country = config['border_countries']
    total = sum(pop_by_border_country.values())
    pop_by_agent_type[AgentType.ADULT] += math.ceil(config['n'] * total/sum(pop_by_age))
    log.info("Agent count by type: %s", pop_by_agent_type)
    # The total numbers of children, adults and retired individuals are fixed deterministically,
    # while the exact age of individuals within each group is determined randomly.
    log.info("Constructing agents...")
    for atype, slce in POPULATION_SLICES.items():
        log.info(" - %s...", atype.name)
        for _ in tqdm(range(pop_by_agent_type[atype])):

            # Sample a point from the age distribution within this slice
            age = (slce.start or 0) + multinoulli(pop_by_age[slce])

            new_agent = Agent(atype, age)
            network.add_agent(new_agent)

def make_house_profile_dictionary(config):
    """Creates a probability distribution across household profiles."""

    log.debug("Making housing dictionary...")

    hshld_dst_children = config['household_distribution_children']
    hshld_dst_retired = config['household_distribution_retired']

    max_house_size = len(hshld_dst_retired[0]) - 1
    assert max_house_size == len(hshld_dst_children[0]) - 1

    total_houses = sum([sum(x) for x in zip(*hshld_dst_retired)])
    assert total_houses == sum([sum(x) for x in zip(*hshld_dst_children)])

    # Each key in the following dictionary, house_profiles, will be a triple. The entries in each
    # triple will correspond to numbers of children, adults and retired, respectively. The
    # corresponding value indicates the probility of that triple occuring as household profile.
    # The sum of the entries in a given triple is bounded by the maximum house size. All possible
    # keys are generated that satisfy this bound.
    #
    # To generate the probabilties, it is assumed that, conditional on the house size being n and
    # the number of retired residents in a house being r, the number of children c follows the
    # distribution given by normalizing the first n-r entries in the n-th column of the matrix
    # hshld_dst_children.

    house_profiles = {}

    for house_size in range(1, max_house_size + 1):
        for num_children in range(house_size + 1):
            for num_retired in range(house_size + 1 - num_children):
                num_adult = house_size - num_children - num_retired
                weight = sum(tuple(zip(*hshld_dst_children))[house_size][0:house_size + 1 - num_retired])
                prob = hshld_dst_children[num_children][house_size]\
                       *hshld_dst_retired[num_retired][house_size]/(total_houses*weight)
                house_profiles[(num_children, num_adult, num_retired)] = prob

    return house_profiles

def assign_homes(network, density_map, config, activity_manager, home_activity_type, carehome_type):
    """Assign homes to agents."""

    log.info("Assigning homes: %s...", home_activity_type)

    unassigned_children = copy.copy(network.agents_by_type[AgentType.CHILD])
    unassigned_adults = copy.copy(network.agents_by_type[AgentType.ADULT])
    unassigned_retired = copy.copy(network.agents_by_type[AgentType.RETIRED])

    # ---- Populate Carehomes ----
    log.debug("Populating care homes...")

    # Number of residents per carehome
    num_retired = config['retired_per_carehome']

    carehomes = copy.copy(network.locations_for_types(carehome_type))

    occupancy_carehomes = {}

    for carehome in carehomes:

        # Take from front of lists
        carehome_residents = unassigned_retired[0:num_retired]
        del unassigned_retired[0:num_retired]

        # Assign agents to carehome
        occupancy_carehomes[carehome] = carehome_residents
        
        for resident in carehome_residents:
            resident.add_activity_location(activity_manager.as_int(home_activity_type), carehome)

    # ---- Populate Border Countries ----
    log.debug("Populating border countries...")   

    # Cross border worker populations
    border_countries = config['border_countries']

    total_pop_by_age = sum(config['age_distribution'])

    occupancy_border_countries = {}

    for border_country in border_countries:

        # Normalize cross border worker populations
        border_country_n = math.ceil(config['n']*border_countries[border_country]/total_pop_by_age)

        # Take from front of lists
        border_country_workers = unassigned_adults[0:border_country_n]
        del unassigned_adults[0:border_country_n]

        country = network.locations_for_types(border_country)[0]

        occupancy_border_countries[country] = border_country_workers

        for worker in border_country_workers:
            worker.add_activity_location(activity_manager.as_int(home_activity_type), country)

    # ---- Populate Houses ----
    log.debug("Populating houses...")

    # Type distribution from which to sample
    house_types = make_house_profile_dictionary(config)

    occupancy_houses = {}

    while len(unassigned_children + unassigned_adults + unassigned_retired) > 0:

        # Create new house and add it to the network
        house_coord = density_map.sample_coord()
        new_house = Location('House', house_coord)
        network.add_location(new_house)

        # Generate household profile
        household_profile = multinoulli_dict(house_types)

        num_children = min(household_profile[0], len(unassigned_children))
        num_adults   = min(household_profile[1], len(unassigned_adults))
        num_retired  = min(household_profile[2], len(unassigned_retired))

        # Take agents from front of lists
        children = unassigned_children[0:num_children]
        del unassigned_children[0:num_children]
        adults = unassigned_adults[0:num_adults]
        del unassigned_adults[0:num_adults]
        retired = unassigned_retired[0:num_retired]
        del unassigned_retired[0:num_retired]

        # Assign agents to new house
        occupancy_houses[new_house] = children + adults + retired

        for occupant in occupancy_houses[new_house]:
            occupant.add_activity_location(activity_manager.as_int(home_activity_type), new_house)

    return occupancy_houses, occupancy_carehomes, occupancy_border_countries

def do_activity_from_home(activity_manager, occupancy, activity_type):
    """Assigns an activity location as the home"""
    for location in occupancy:
        for agent in occupancy[location]:
            agent.add_activity_location(activity_manager.as_int(activity_type), location)

def make_work_profile_dictionary(network, config):
    """Generates weights for working locations"""
    workforce_profile_histogram = config['workforce_profile_histogram']
    profile_format = config['workforce_profile_histogram_format']
    # Weights reflect typical size of workforce in locations across different sectors
    workplace_weights = {}
    for location_type in workforce_profile_histogram:
        profile = workforce_profile_histogram[location_type]
        for location in network.locations_by_type[location_type]:
            interval = profile_format[multinoulli(profile)]
            weight = random_randrange_interval(interval[0],interval[1])
            workplace_weights[location] = weight

    return workplace_weights

def assign_workplaces(network, config, activity_manager, work_activity_type, occupancy_houses,
                      occupancy_carehomes, occupancy_border_countries):
    """Assign a place of work for each agent."""

    log.info("Assigning places of work: %s...", work_activity_type)

    log.debug("Assigning workplace to house occupants...")

    workplace_weights = make_work_profile_dictionary(network, config)

    for house in tqdm(occupancy_houses):
        for agent in occupancy_houses[house]:
            workplace = multinoulli_dict(workplace_weights)
            agent.add_activity_location(activity_manager.as_int(work_activity_type), workplace)

    log.debug("Assigning workplace to border country occupants...")

    for border_country in occupancy_border_countries:
        for agent in occupancy_border_countries[border_country]:
            workplace = multinoulli_dict(workplace_weights)
            agent.add_activity_location(activity_manager.as_int(work_activity_type), workplace)

    log.debug("Assigning workplace to carehome occupants...")

    do_activity_from_home(activity_manager, occupancy_carehomes, work_activity_type)

def assign_other_houses(network, config, activity_manager, home_activity_type,
                        other_house_activity_type, occupancy_houses, occupancy_carehomes,
                        occupancy_border_countries):
    """Assign other houses agents may visit"""
    # For each individual, a number of distinct homes, not including the individual's own home, are
    # randomly selected so that the individual is able to visit them:
    log.info("Assigning house visit locations: %s...", other_house_activity_type)

    visit_locations = network.locations_for_types(activity_manager.get_location_types(other_house_activity_type))    

    log.debug("Assigning house visit locations to house occupants...")

    for house in tqdm(occupancy_houses):
        for agent in occupancy_houses[house]:
            # This may select k-1 if the agent's current home is in the samole
            houses_to_visit = random_sample(visit_locations, k=config['homes_allowed_to_visit'])

            # Blacklist the agent's own home
            agent_own_home = agent.activity_locations[activity_manager.as_int(home_activity_type)]
            houses_to_visit = [h for h in houses_to_visit if h not in agent_own_home]

            agent.add_activity_location(activity_manager.as_int(other_house_activity_type),
                                        houses_to_visit)

    log.debug("Assigning workplace to border country occupants...")

    do_activity_from_home(activity_manager, occupancy_border_countries, other_house_activity_type)

    log.debug("Assigning workplace to carehome occupants...")

    do_activity_from_home(activity_manager, occupancy_carehomes, other_house_activity_type)

def assign_entertainment_venues(network, config, activity_manager, entertainment_activity_type,
                                occupancy_houses, occupancy_carehomes, occupancy_border_countries):
    """Assign some entertainment venues for agents to visit"""
    # For each agent, a number of distinct entertainment venues are randomly selected.
    # First we ensure there is one of each
    log.info("Assigning entertainment venues: %s...", entertainment_activity_type)

    venues = network.locations_for_types(activity_manager.get_location_types(entertainment_activity_type))

    log.debug("Assigning entertainment venues to house occupants...")

    for house in tqdm(occupancy_houses):
        for agent in occupancy_houses[house]:
            num_locations = max(1, random_randrange(config['max_entertainment_allowed_to_visit']))
            new_entertainments = random_sample(venues, k=min(len(venues), num_locations))
            agent.add_activity_location(activity_manager.as_int(entertainment_activity_type),
                                        new_entertainments)

    log.debug("Assigning entertainment venues to border country occupants...")

    do_activity_from_home(activity_manager, occupancy_border_countries, entertainment_activity_type)

    log.debug("Assigning entertainment venues to carehome occupants...")

    do_activity_from_home(activity_manager, occupancy_carehomes, entertainment_activity_type)


def assign_householders_by_proximity(network, activity_manager, activity_type, occupancy_houses,
                                     occupancy_carehomes, occupancy_border_countries):
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
    log.debug("Assigning proximate locations to house occupants...")
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

        for occupant in occupancy_houses[house]:
            occupant.add_activity_location(activity_manager.as_int(activity_type), closest_location)

    log.debug("Assigning proximate locations to border country occupants...")

    do_activity_from_home(activity_manager, occupancy_border_countries, activity_type)

    log.debug("Assigning proximate locations to carehome occupants...")

    do_activity_from_home(activity_manager, occupancy_carehomes, activity_type)

def assign_outdoors(network, activity_manager, outdoor_activity_type, occupancy_houses,
                    occupancy_carehomes, occupancy_border_countries):
    """Ensure all residents except carehome residents are allowed to access the outdoors"""

    log.info("Assigning outdoor location for activity %s...", outdoor_activity_type)

    outdoor_locations = network.locations_for_types(activity_manager.get_location_types(outdoor_activity_type))

    #The outdoors is treated as a single environment in which zero disease transmission will occur:
    if len(outdoor_locations) != 1:
        raise ValueError("More than one outdoor location found.  This shouldn't be.")

    log.debug("Assigning outdoor location to house occupants...")

    for house in tqdm(occupancy_houses):
        for agent in occupancy_houses[house]:
            agent.add_activity_location(activity_manager.as_int(outdoor_activity_type),
                                        outdoor_locations[0])
                                    
    log.debug("Assigning outdoor location to border country occupants...")

    do_activity_from_home(activity_manager, occupancy_border_countries, outdoor_activity_type)

    log.debug("Assigning outdoor location to carehome occupants...")

    do_activity_from_home(activity_manager, occupancy_carehomes, outdoor_activity_type)


def assign_cars(network, activity_manager, car_activity_type, occupancy_houses, occupancy_carehomes,
                occupancy_border_countries):
    """Assign cars to houses.  This ensures all occupants at the house see the "car" activity
    as using that particular car"""

    log.info("Assigning car location for activity %s...", car_activity_type)

    houses = network.locations_by_type['House']

    log.debug("Assigning car to house occupants...")

    for house in tqdm(occupancy_houses):

        new_car = Location('Car', house.coord)
        network.add_location(new_car)

        for agent in occupancy_houses[house]:
            agent.add_activity_location(activity_manager.as_int(car_activity_type), new_car)

    log.debug("Assigning car to border country occupants...")

    do_activity_from_home(activity_manager, occupancy_border_countries, car_activity_type)

    log.debug("Assigning car to carehome occupants...")

    do_activity_from_home(activity_manager, occupancy_carehomes, car_activity_type)

def build_network_model(config, density_map):
    """Create agents and locations according to the population density map given"""

    activity_manager = ActivityManager(config['activities'])

    # Create and populate the network
    log.info("Creating network")
    network = Network(density_map)
    create_agents(network, config)
    create_locations(network, density_map, config)

    log.info("Assigning locations to agents...")
    occupancy_houses, occupancy_carehomes, occupancy_border_countries \
    = assign_homes(network, density_map, config, activity_manager, "House", "Care Home")
    assign_workplaces(network, config, activity_manager, "Work", occupancy_houses, occupancy_carehomes,
                      occupancy_border_countries)
    assign_other_houses(network, config, activity_manager, "House", "Other House", occupancy_houses,
                        occupancy_carehomes, occupancy_border_countries)

    for entertainment_activity_type in config['entertainment_activities']:
        assign_entertainment_venues(network, config, activity_manager, entertainment_activity_type,
                                    occupancy_houses, occupancy_carehomes,
                                    occupancy_border_countries)

    for activity_type in config['whole_household_activities']:
        assign_householders_by_proximity(network, activity_manager, activity_type, occupancy_houses,
                                         occupancy_carehomes, occupancy_border_countries)

    assign_outdoors(network, activity_manager, "Outdoor", occupancy_houses, occupancy_carehomes,
                    occupancy_border_countries)
    assign_cars(network, activity_manager, "Car", occupancy_houses, occupancy_carehomes,
                occupancy_border_countries)

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
