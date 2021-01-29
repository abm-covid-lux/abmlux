"""This file procedurally generates the agents and locations."""

import math
import copy
import logging
from collections import defaultdict
import numpy as np

from tqdm import tqdm
from scipy.spatial import KDTree

from abmlux.random_tools import Random
from abmlux.agent import Agent
from abmlux.location import Location, WGS84_to_ETRS89
from abmlux.world import World
from abmlux.world.world_factory import WorldFactory

log = logging.getLogger('stochastic_world_factory')

class StochasticWorldFactory(WorldFactory):
    """Reads a DensityMap and generates a world based on the densities indicated therein."""

    def __init__(self, _map, activity_manager, config):
        """Create agents and locations according to the population density map given"""

        self.map                  = _map
        self.config               = config
        self.activity_manager     = activity_manager
        self.prng                 = Random(config['__prng_seed__'])
        self.location_choice_fp   = config['location_choice_fp']
        self.resident_nationality = config['resident_nationality']

    def get_world(self) -> World:

        log.info("Creating world...")

        world = World(self.map)
        self._create_agents(world, self.resident_nationality)
        self._create_locations(world)

        log.info("Assigning locations to agents...")

        # Assign homes
        # FIXME: remove literals
        occupancy_houses, occupancy_carehomes, = self._assign_homes(world, "House", "House", "Care Home")
        occupancy_border_countries = self._create_border_country_populations(world, "House")
        # Assign workplaces
        # FIXME: remove literals
        self._assign_workplaces(world, "Work", occupancy_houses,
                        occupancy_carehomes, occupancy_border_countries)
        # Assignments of locations by distance
        for activity_type in self.config['activity_locations_by_distance']:
            self._assign_locations_by_distance(world, activity_type,
                                        occupancy_houses, occupancy_carehomes,
                                        occupancy_border_countries)
        # Assignments of locations by random
        for activity_type in self.config['activity_locations_by_random']:
            self._assign_locations_by_random(world, activity_type,
                                    occupancy_houses, occupancy_carehomes,
                                    occupancy_border_countries)
        # Assign schools
        for activity_type in self.config['school_locations_by_proximity']:
            self._assign_schools(world, "Work", activity_type,
                                        occupancy_houses, occupancy_carehomes,
                                        occupancy_border_countries)
        # Assignments of locations by proximity
        for activity_type in self.config['activity_locations_by_proximity']:
            self._assign_locations_by_proximity(world, activity_type,
                                        occupancy_houses, occupancy_carehomes,
                                        occupancy_border_countries)
        # Assignments of outdoors
        self._assign_outdoors(world, "Outdoor", occupancy_houses, occupancy_carehomes,
                              occupancy_border_countries)
        # Assignments of cars
        self._assign_cars(world, "Car", "Car", occupancy_houses, occupancy_carehomes,
                          occupancy_border_countries)

        return world

    def _create_locations(self, world):
        """Create a number of Location objects within the world, according to the density map
        given and the distributions defined in the config. Locations with a non-deterministic count are
        created later."""

        log.debug('Initializing locations...')

        location_counts = self.config['deterministic_location_counts']
        pop_by_age      = self.config['age_distribution']

        # Adjust location counts by the ratio of the simulation size and real population size
        location_counts = {typ: math.ceil((self.config['n'] / sum(pop_by_age)) * location_counts[typ])
                           for typ, x in location_counts.items()}
        location_counts['Outdoor'] = 1
        log.debug("Location count by type: %s", location_counts)
        # Create locations for each type, of the amounts requested
        log.info("Constructing locations...")
        for ltype, lcount in location_counts.items():
            for _ in range(lcount):
                new_coord = world.map.sample_coord()
                new_location = Location(ltype, new_coord)
                world.add_location(new_location)

    def _create_agents(self, world, resident_nationality):
        """Create a number of Agent objects within the world, according to the distributions
        specified in the configuration object provided."""

        log.debug('Initializing agents...')

        pop_by_age = self.config['age_distribution']

        # How many agents per agent type
        world.set_scale_factor(self.config['n'] / sum(pop_by_age))
        pop_normalised = [math.ceil(x * world.scale_factor) for x in pop_by_age]
        log.info("Creating %i resident agents...", sum(pop_normalised))
        for age, pop in tqdm(enumerate(pop_normalised)):
            for _ in range(pop):
                new_agent = Agent(age, resident_nationality)
                world.add_agent(new_agent)

    def _make_house_profile_dictionary(self):
        """Creates a probability distribution across household profiles."""

        log.debug("Making housing dictionary...")

        hshld_dst_c = self.config['household_distribution_children']
        hshld_dst_r = self.config['household_distribution_retired']

        max_house_size = len(hshld_dst_r[0]) - 1
        if max_house_size != len(hshld_dst_c[0]) - 1:
            raise Exception("Distributions of children and retired are in conflict: max house size")
        total_houses = sum([sum(x) for x in zip(*hshld_dst_r)])
        if total_houses != sum([sum(x) for x in zip(*hshld_dst_c)]):
            raise Exception("Distributions of children and retired are in conflict: total houses")
        # Each key in the following dictionary, house_profiles, will be a triple. The entries in each
        # triple will correspond to numbers of children, adults and retired, respectively. The
        # corresponding value indicates the probility of that triple occuring as household profile.
        # The sum of the entries in a given triple is bounded by the maximum house size. All possible
        # keys are generated that satisfy this bound.
        #
        # To generate the probabilties, it is assumed that, conditional on the house size being n and
        # the number of retired residents in a house being r, the number of children c follows the
        # distribution given by normalizing the first n-r entries in the n-th column of the matrix
        # hshld_dst_c, averaged against the probability obtained by calculating the same quantity
        # with the roles of children and retired interchanged.
        house_profiles = {}
        for house_size in range(1, max_house_size + 1):
            for num_children in range(house_size + 1):
                for num_retired in range(house_size + 1 - num_children):
                    num_adult = house_size - num_children - num_retired
                    weight_1 = sum(tuple(zip(*hshld_dst_c))[house_size][0:house_size + 1 - num_retired])
                    prob_1 = hshld_dst_c[num_children][house_size]\
                        * hshld_dst_r[num_retired][house_size] / (total_houses*weight_1)
                    weight_2 = sum(tuple(zip(*hshld_dst_r))[house_size][0:house_size + 1 - num_children])
                    prob_2 = hshld_dst_r[num_retired][house_size]\
                        * hshld_dst_c[num_children][house_size] / (total_houses*weight_2)
                    house_profiles[(num_children, num_adult, num_retired)] = (prob_1 + prob_2)/2

        return house_profiles

    def _assign_homes(self, world, house_location_type, home_activity_type,
                      carehome_type):
        """Assigns homes to agents."""

        log.info("Creating and populating homes...")

        child_age_limit   = self.config['child_age_limit']
        retired_age_limit = self.config['retired_age_limit']

        children, adults, retired = [], [], []
        for agent in world.agents:
            if agent.age in range(0, child_age_limit):
                children.append(agent)
            if agent.age in range(child_age_limit, retired_age_limit):
                adults.append(agent)
            if agent.age in range(retired_age_limit, 120):
                retired.append(agent)

        unassigned_children = copy.copy(children)
        self.prng.random_shuffle(unassigned_children)
        unassigned_adults   = copy.copy(adults)
        self.prng.random_shuffle(unassigned_adults)
        unassigned_retired  = copy.copy(retired)
        
        # ---- Populate Carehomes ----
        log.debug("Populating care homes...")
        # Number of residents per carehome
        carehomes = copy.copy(world.locations_for_types(carehome_type))
        retired_per_carehome = min(self.config['retired_per_carehome'],
                                   max(int(len(unassigned_retired)/len(carehomes)),1))
        total_retired_in_carehomes = retired_per_carehome * len(carehomes)
        carehome_residents = unassigned_retired[-total_retired_in_carehomes:]
        del unassigned_retired[-total_retired_in_carehomes:]
        occupancy_carehomes = {}
        for carehome in carehomes:
            # Randomly sample from the potential residents
            residents = self.prng.random_sample(carehome_residents, k = retired_per_carehome)
            # Assign agents to carehome and remove from list of availables
            occupancy_carehomes[carehome] = residents
            for agent in residents:
                carehome_residents.remove(agent)
                agent.add_activity_location(self.activity_manager.as_int(home_activity_type), carehome)
        self.prng.random_shuffle(unassigned_retired)

        # ---- Populate Houses ----
        log.debug("Populating houses...")
        # Type distribution from which to sample
        house_types = self._make_house_profile_dictionary()
        occupancy_houses = {}
        while len(unassigned_children + unassigned_adults + unassigned_retired) > 0:
            # Generate household profile
            household_profile = self.prng.multinoulli_dict(house_types)
            num_children = min(household_profile[0], len(unassigned_children))
            num_adults   = min(household_profile[1], len(unassigned_adults))
            num_retired  = min(household_profile[2], len(unassigned_retired))
            # Take agents from front of lists
            children = unassigned_children[0:num_children]
            adults = unassigned_adults[0:num_adults]
            retired = unassigned_retired[0:num_retired]
            # If some agents are found then create a new house
            if len(children + adults + retired) > 0:
                del unassigned_children[0:num_children]
                del unassigned_adults[0:num_adults]
                del unassigned_retired[0:num_retired]
                # Create new house and add it to the world
                house_coord = world.map.sample_coord()
                new_house = Location(house_location_type, house_coord)
                world.add_location(new_house)
                # Assign agents to new house
                occupancy_houses[new_house] = children + adults + retired
                for occupant in occupancy_houses[new_house]:
                    occupant.add_activity_location(self.activity_manager.as_int(home_activity_type), new_house)

        return occupancy_houses, occupancy_carehomes

    def _do_activity_from_home(self, occupancy, activity_type):
        """Sets the activity location as the occupancy location, for all agents listed in an
        occupancy dictionary."""

        for location in occupancy:
            for agent in occupancy[location]:
                agent.add_activity_location(self.activity_manager.as_int(activity_type), location)

    def _create_border_country_populations(self, world, home_activity_type):
        """Create agents and populate them in the border countries"""

        # Create locations of each border country
        pop_by_age             = self.config['age_distribution']
        min_age_border_workers = self.config['min_age_border_workers']
        max_age_border_workers = self.config['max_age_border_workers']
        pop_by_border_country  = self.config['border_countries_pop']
        border_country_coord   = self.config['border_country_coord']

        total = sum(pop_by_border_country.values()) * world.scale_factor
        log.info("Creating %i cross-border workers...", total)
        occupancy_border_countries = defaultdict(list)
        border_worker_ages = list(range(min_age_border_workers, max_age_border_workers + 1))
        border_worker_ages_dist = pop_by_age[min_age_border_workers:max_age_border_workers + 1]
        for country in pop_by_border_country:
            coord = WGS84_to_ETRS89((border_country_coord[country][0], border_country_coord[country][1]))
            country_location = Location(country, (coord[1], coord[0]))
            world.add_location(country_location)
            total_pop = pop_by_border_country[country] * world.scale_factor
            for _ in range(int(total_pop)):
                age = self.prng.random_choices(border_worker_ages, border_worker_ages_dist, 1)[0]
                new_agent = Agent(age, country)
                world.add_agent(new_agent)
                new_agent.add_activity_location(self.activity_manager.as_int(home_activity_type), country_location)
                occupancy_border_countries[country_location].append(new_agent)

        return occupancy_border_countries

    def _make_distribution(self, motive, country_origin, country_destination, number_of_bins, bin_width):
        """For given country  of origin, country of destination and motive, this creates a probability
        distribution over ranges of distances."""

        log.debug("Generating distance distribution...")

        actsheet = np.genfromtxt(self.location_choice_fp, dtype=str, delimiter=",")

        max_row = np.shape(actsheet)[0]

        # In the following distribution, the probability assigned to a given range reflects the
        # probability that the length of a trip, between the input countries and with the given
        # motivation, falls within that range. Note that the units of bid_width are kilometers, and that
        # the distances recorded in the data refer to distance travelled by the respondent, not as the
        # crow flies.
        distance_distribution = {}
        for bin_num in range(number_of_bins):
            distance_distribution[range(bin_width*bin_num,bin_width*(bin_num+1))] = 0
        for sheet_row in range(1,max_row):
            motive_sample = actsheet[sheet_row][0]
            country_origin_sample = actsheet[sheet_row][1]
            country_destination_sample = actsheet[sheet_row][2]
            # For each sample of the desired trip type, record the distance and add to the distribution
            if ([motive_sample,country_origin_sample,country_destination_sample]
                == [motive, country_origin, country_destination]):
                distance_str = actsheet[sheet_row][3]
                if distance_str != "Na":
                    distance = float(distance_str)
                    if distance < number_of_bins*bin_width:
                        weight = float(actsheet[sheet_row][4])
                        distance_distribution[range(int((distance//bin_width)*bin_width),
                                int(((distance//bin_width)+1)*bin_width))] += round(weight)
        # Normalize to obtain a probability distribution
        total_weight = sum(distance_distribution.values())
        for distribution_bin in distance_distribution:
            distance_distribution[distribution_bin] /= total_weight

        return distance_distribution

    def _road_distance(self, euclidean_distance_km):
        # FIXME: move this into the world model somehow
        """Converts a Euclidean distance into a world distance."""

        alpha = self.config['alpha']
        beta  = self.config['beta']

        return (euclidean_distance_km * alpha) + beta

    def _get_weight(self, dist_km, distance_distribution):
        """Given a distance, in kilometers, and a distance_distribution, returns the probability weight
        associated to that distance by the distribution."""

        dist_length = sum([len(dist_bin) for dist_bin in list(distance_distribution.keys())])
        if int(self._road_distance(dist_km)) >= dist_length:
            return 0.0  # FIXME: this causes some calls to random weighted selection with 0 weights

        for distribution_bin in distance_distribution:
            if int(self._road_distance(dist_km)) in distribution_bin:
                return distance_distribution[distribution_bin]

    def _make_work_profile_dictionary(self, world):
        """Generates weights for working locations"""

        workforce_profile_distribution = self.config['workforce_profile_distribution']
        workforce_profile_uniform      = self.config['workforce_profile_uniform']
        profile_format                 = self.config['workforce_profile_distribution_format']

        # Weights reflect typical size of workforce in locations across different sectors
        workplace_weights = {}
        for location_type in workforce_profile_distribution:
            profile = workforce_profile_distribution[location_type]
            for location in world.locations_by_type[location_type]:
                interval = profile_format[self.prng.multinoulli(profile)]
                weight = self.prng.random_randrange_interval(interval[0],interval[1])
                workplace_weights[location] = weight
        for location_type in workforce_profile_uniform:
            weight = workforce_profile_uniform[location_type]
            for location in world.locations_by_type[location_type]:
                workplace_weights[location] = weight

        return workplace_weights

    def _assign_workplaces(self, world, work_activity_type, occupancy_houses,
                           occupancy_carehomes, occupancy_border_countries):
        """Assign a place of work for each agent."""

        log.info("Assigning places of work...")

        bin_width           = self.config['bin_width']
        number_of_bins      = self.config['number_of_bins']
        sample_size         = self.config['location_sample_size']
        destination_country = self.config['destination_country']
        origin_country_dict = self.config['origin_country_dict']
        activity_dict       = self.config['activity_dict']

        # These determine the probability of an agent travelling a distance to work
        work_dist_dict = {}
        for country in origin_country_dict:
            work_dist_dict[country] = self._make_distribution(activity_dict[work_activity_type],
                                                        origin_country_dict[country],
                                                        destination_country,
                                                        number_of_bins[country], bin_width[country])

        log.info("Generating workforce weights...")
        # These weights corrspond to the size of the workforce at each workplace
        workplace_weights = self._make_work_profile_dictionary(world)
        log.info("Assigning workplaces to house occupants...")
        wrkplaces = world.locations_for_types(self.activity_manager.get_location_types(work_activity_type))
        for house in tqdm(occupancy_houses):
            # Here each house gets a sample from which occupants choose
            work_locations_sample = self.prng.random_sample(wrkplaces, k = min(sample_size, len(wrkplaces)))
            weights_for_house = {}
            for location in work_locations_sample:
                dist_m = house.distance_euclidean(location)
                dist_km = dist_m/1000
                weight = self._get_weight(dist_km, work_dist_dict['Luxembourg'])
                # For each location, the workforce weights and distance weights are multiplied
                weights_for_house[location] = workplace_weights[location] * weight
            for agent in occupancy_houses[house]:
                # A workplace is then chosen randomly from the sample, according to the weights
                workplace = self.prng.multinoulli_dict(weights_for_house)
                agent.add_activity_location(self.activity_manager.as_int(work_activity_type), workplace)
            weights_for_house.clear()

        log.info("Assigning workplaces to border country occupants...")
        for border_country in occupancy_border_countries:
            for agent in tqdm(occupancy_border_countries[border_country]):
                # Here each agent gets a sample from which to choose
                work_locations_sample = self.prng.random_sample(wrkplaces,k=min(sample_size, len(wrkplaces)))
                weights_for_agent = {}
                for location in work_locations_sample:
                    dist_m = border_country.distance_euclidean(location)
                    dist_km = dist_m/1000
                    weight = self._get_weight(dist_km, work_dist_dict[border_country.typ])
                    weights_for_agent[location] = workplace_weights[location] * weight
                workplace = self.prng.multinoulli_dict(weights_for_agent)
                agent.add_activity_location(self.activity_manager.as_int(work_activity_type), workplace)
                weights_for_agent.clear()

        log.debug("Assigning workplaces to carehome occupants...")
        self._do_activity_from_home(occupancy_carehomes, work_activity_type)

    def _assign_locations_by_distance(self, world, activity_type, occupancy_houses,
                                      occupancy_carehomes, occupancy_border_countries):
        """Assign activities to agents by distance"""
        # For each individual, a number of distinct locations, not including the individual's own home,
        # are randomly selected so that the individual is able to visit them:
        log.info("Assigning locations by distance for activity: %s...", activity_type)

        bin_width      = self.config['bin_width']
        number_of_bins = self.config['number_of_bins']
        num_can_visit  = self.config['activity_locations_by_distance']
        sample_size    = self.config['location_sample_size']
        activity_dict  = self.config['activity_dict']

        vst_locs = world.locations_for_types(self.activity_manager.get_location_types(activity_type))
        # This determines the probability of an agent travelling a distance for a house visit
        dist_dict = self._make_distribution(activity_dict[activity_type], 'Luxembourg', 'Luxembourg',
                                            number_of_bins['Luxembourg'], bin_width['Luxembourg'])
        log.debug("Assigning locations to house occupants...")
        for house in tqdm(occupancy_houses):
            visit_locations_sample = self.prng.random_sample(vst_locs, k=min(sample_size, len(vst_locs)))
            weights_for_house = {}
            for location in visit_locations_sample:
                dist_m = house.distance_euclidean(location)
                dist_km = dist_m/1000
                weights_for_house[location] = self._get_weight(dist_km, dist_dict)
            if sum(list(weights_for_house.values())) == 0:
                for h in list(weights_for_house.keys()):
                    weights_for_house[h] = 1
            for agent in occupancy_houses[house]:
                # Several houses are then chosen randomly from the sample, according to the weights
                locs = self.prng.random_choices(list(weights_for_house.keys()),
                                        list(weights_for_house.values()), num_can_visit[activity_type])
                # If the activity is visit and the agent's own home is chosen, then it is removed from
                # the list and the sample can therefore be of size num_can_visit['Visit']-1
                if (activity_type == 'Visit') and (house in locs):
                    locs.remove(house)
                agent.add_activity_location(self.activity_manager.as_int(activity_type), locs)
            weights_for_house.clear()
        log.debug("Assigning locations to border country occupants...")
        self._do_activity_from_home(occupancy_border_countries, activity_type)
        log.debug("Assigning locations to carehome occupants...")
        self._do_activity_from_home(occupancy_carehomes, activity_type)

    def _assign_locations_by_random(self, world, activity_type,
                                occupancy_houses, occupancy_carehomes, occupancy_border_countries):
        """For each agent, a number of distinct locations are randomly selected"""

        log.info("Assigning locations by random for activity: %s...", activity_type)

        num_can_visit = self.config['activity_locations_by_random']

        venues = world.locations_for_types(self.activity_manager.get_location_types(activity_type))
        log.debug("Assigning locations by random to house occupants...")
        for house in tqdm(occupancy_houses):
            for agent in occupancy_houses[house]:
                venues_sample = self.prng.random_sample(venues, k=min(len(venues),
                                                num_can_visit[activity_type]))
                agent.add_activity_location(self.activity_manager.as_int(activity_type), venues_sample)
        log.debug("Assigning locations by random to border country occupants...")
        self._do_activity_from_home(occupancy_border_countries, activity_type)
        log.debug("Assigning locations by random to carehome occupants...")
        self._do_activity_from_home(occupancy_carehomes, activity_type)

    def _kdtree_assignment(self, world, locations):
        """For the locations given, select nearby houses and assign houses to these locations.
        If the location is full, move to the next nearby location, etc."""

        # The following code assigns homes to locations in such a way that equal numbers of homes are
        # assigned to each location in the given list. For example, from the list of homes, a home is
        # randomly selected and assigned to the nearest school, unless that school has already been
        # assigned its share of homes, in which case the next nearest available school is assigned.
        # This creates local spatial structure while ensuring that no school, for example, is
        # assigned more homes than the other schools. This same procedure is also applied to medical
        # locations, places of worship and indoor sport:

        log.debug("Found %i available locations", len(locations))
        assert len(locations) > 0

        max_homes  = math.ceil(world.count('House') / len(locations))
        kdtree     = KDTree([l.coord for l in locations])
        num_houses = defaultdict(int)

        locations_dict = {}

        # Traverse houses in random order, assigning a school of type school_type to each house
        shuffled_houses = copy.copy(world.locations_by_type['House'])
        self.prng.random_shuffle(shuffled_houses)
        for house in tqdm(shuffled_houses):
            # Find the closest location and, if it's not full, assign every occupant to the location
            knn = 2
            closest_locations = []
            while len(closest_locations) == 0:
                if (knn/2) > len(locations):
                    raise ValueError("Searching for more locations than exist."
                                     "This normally indicates that all locations are full.")
                # Returns knn items, in order of nearness
                _, nearest_indices = kdtree.query(house.coord, knn)
                closest_locations = [locations[i] for i in nearest_indices if i < len(locations)]
                # Remove locations that have too many houses already
                closest_locations = [x for x in closest_locations if num_houses[x] < max_homes]
                knn *= 2
            closest_location = closest_locations[0]
            # Add all occupants of this house to the location, unless they are under age
            num_houses[closest_location] += 1
            locations_dict[house] = closest_location

        return locations_dict

    def _assign_schools(self, world, work_activity, activity_type,
                        occupancy_houses, occupancy_carehomes, occupancy_border_countries):
        """For the schools of each type given, select nearby houses and assign all occupants to
        attend this school. If the school is full, move to the next nearby school, etc."""

        log.debug("Assigning proximate locations for activity: %s...", activity_type)

        log.debug("Assigning proximate locations to house occupants...")
        log.debug("Finding people to perform activity: %s", activity_type)
        log.debug("Location types: %s", self.activity_manager.get_location_types(activity_type))

        # The different types of school, e.g. Primary School, Secondary School etc.
        types_of_school        = self.activity_manager.get_location_types(activity_type)
        num_classes_per_school = self.config['num_classes_per_school']
        schools_dict = defaultdict(dict)
        classes_dict = defaultdict(list)

        # Assign a school of each type to each house by proximity:
        for school_type in types_of_school:
            log.info("Assigning schools of type: %s...", school_type)
            locations = world.locations_for_types(school_type)
            schools_dict[school_type] = self._kdtree_assignment(world, locations)

        # Generate additional instances of each school, the total number in a specified location
        # being the number of classes in the school:
        for school_type in types_of_school:
            for school in world.locations_for_types(school_type):
                classes_dict[school].append(school)
                for _ in range(num_classes_per_school[school_type] - 1):
                    new_class = Location(school_type, school.coord)
                    world.add_location(new_class)
                    classes_dict[school].append(new_class)

        # Redistribute teachers across classrooms
        work_activity_int = self.activity_manager.as_int(work_activity)
        for agent in world.agents:
            workplaces = agent.locations_for_activity(work_activity_int)
            if len(workplaces) == 0:
                log.warning("Found no workplaces for agent %s, activity type %s", agent, work_activity)
                continue

            workplace = workplaces[0]
            if workplace.typ in types_of_school:
                agent.locations_for_activity(work_activity_int).remove(workplace)
                assigned_class = self.prng.random_choice(classes_dict[workplace])
                agent.locations_for_activity(work_activity_int).append(assigned_class)

        # Assign a class to each house occupant based on age:
        starting_age   = self.config['starting_age']
        min_school_age = min(starting_age.keys())
        for house in occupancy_houses:
            for occupant in occupancy_houses[house]:
                if occupant.age < min_school_age:
                    occupant.add_activity_location(self.activity_manager.as_int(activity_type), house)
                else:
                    age_key = max([a for a in starting_age.keys() if a <= occupant.age])
                    type_of_school = starting_age[age_key]
                    closest_school = schools_dict[type_of_school][house]
                    school_class   = self.prng.random_choice(classes_dict[closest_school])
                    occupant.add_activity_location(self.activity_manager.as_int(activity_type), school_class)

        log.debug("Assigning proximate locations to border country occupants...")
        self._do_activity_from_home(occupancy_border_countries, activity_type)
        log.debug("Assigning proximate locations to carehome occupants...")
        self._do_activity_from_home(occupancy_carehomes, activity_type)

    def _assign_locations_by_proximity(self, world, activity_type,
                                    occupancy_houses, occupancy_carehomes, occupancy_border_countries):
        """For the location type given, select nearby houses and assign all occupants to
        attend this location.  If the location is full, move to the next nearby location, etc."""

        log.info("Assigning proximate locations for activity: %s...", activity_type)

        log.debug("Assigning proximate locations to house occupants...")
        log.debug("Finding people to perform activity: %s", activity_type)
        log.debug("Location types: %s", self.activity_manager.get_location_types(activity_type))

        # Assign a location to each house by proximity:
        locations = world.locations_for_types(self.activity_manager.get_location_types(activity_type))
        locations_dict = self._kdtree_assignment(world, locations)

        # Assign a location to each house occupant:
        for house in occupancy_houses:
            for occupant in occupancy_houses[house]:
                closest_location = locations_dict[house]
                occupant.add_activity_location(self.activity_manager.as_int(activity_type), closest_location)

        log.debug("Assigning proximate locations to border country occupants...")
        self._do_activity_from_home(occupancy_border_countries, activity_type)
        log.debug("Assigning proximate locations to carehome occupants...")
        self._do_activity_from_home(occupancy_carehomes, activity_type)

    def _assign_outdoors(self, world, outdoor_activity_type, occupancy_houses,
                              occupancy_carehomes, occupancy_border_countries):
        """Ensure all residents except carehome residents are allowed to access the outdoors"""

        log.info("Assigning outdoor location...")

        outdrs = world.locations_for_types(self.activity_manager.get_location_types(outdoor_activity_type))
        #The outdoors is treated as a single environment, in which zero disease transmission will occur
        if len(outdrs) != 1:
            raise ValueError("More than one outdoor location found. Set outdoor count to 1.")
        outdrs_loc = outdrs[0]
        log.debug("Assigning outdoor location to house occupants...")
        for house in tqdm(occupancy_houses):
            for agent in occupancy_houses[house]:
                agent.add_activity_location(self.activity_manager.as_int(outdoor_activity_type), outdrs_loc)
        log.debug("Assigning outdoor location to border country occupants...")
        self._do_activity_from_home(occupancy_border_countries, outdoor_activity_type)
        log.debug("Assigning outdoor location to carehome occupants...")
        self._do_activity_from_home(occupancy_carehomes, outdoor_activity_type)

    def _assign_cars(self, world, car_activity_type, car_location_type, occupancy_houses,
                    occupancy_carehomes, occupancy_border_countries):
        """Assign a car to each house. All occupants of a house use the same car."""

        log.info("Assigning car locations...")

        log.debug("Assigning car to house occupants...")
        for house in tqdm(occupancy_houses):
            new_car = Location(car_location_type, house.coord)
            world.add_location(new_car)
            for agent in occupancy_houses[house]:
                agent.add_activity_location(self.activity_manager.as_int(car_activity_type), new_car)
        log.debug("Assigning car to border country occupants...")
        self._do_activity_from_home(occupancy_border_countries, car_activity_type)
        log.debug("Assigning car to carehome occupants...")
        self._do_activity_from_home(occupancy_carehomes, car_activity_type)
