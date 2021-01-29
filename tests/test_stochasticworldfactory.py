"""Test the stochastic world model"""

from collections import defaultdict
import os
import os.path as osp
import unittest
import logging
import sys
from abmlux.agent import Agent
from abmlux.utils import instantiate_class
from abmlux.location import Location, ETRS89_to_WGS84
from abmlux.activity_manager import ActivityManager
from abmlux.world import World
from abmlux.world.world_factory import WorldFactory
from abmlux.sim_state import SimulationFactory
from abmlux.config import Config


from abmlux.world.map_factory.uniform import UniformMapFactory
from abmlux.world.world_factory.stochastic import StochasticWorldFactory

class TestStochasticWorldFactory(unittest.TestCase):
    """Test the stochastic world model"""

    def test_world_factory(self):

        config = Config("tests/test_configs/test_config_1.yaml")
        sim_factory = SimulationFactory(config)

        config = sim_factory.config

        # -----------------------------------[ World ]---------------------------------

        # Create the map
        map_factory_class = config['map_factory.__type__']
        map_factory_config = config.subconfig('map_factory')
        map_factory = instantiate_class("abmlux.world.map_factory", map_factory_class,
                                        map_factory_config)
        _map = map_factory.get_map()
        sim_factory.set_map(_map)

        # Create the world, providing it with the map
        world_factory_class = config['world_factory.__type__']
        world_factory_config = config.subconfig('world_factory')
        world_factory = instantiate_class('abmlux.world.world_factory', world_factory_class, sim_factory.map,
                                        sim_factory.activity_manager, world_factory_config)

        world = world_factory.get_world()
        sim_factory.set_world_model(world)

        activity_manager = sim_factory.activity_manager

        assert world.scale_factor == 1

        assert len(world.agents) == 1110

        assert len({a for a in world.agents if a.nationality == 'Luxembourg'}) == 960
        assert len({a for a in world.agents if a.nationality == 'Belgium'}) == 50
        assert len({a for a in world.agents if a.nationality == 'France'}) == 50
        assert len({a for a in world.agents if a.nationality == 'Germany'}) == 50

        for agent in world.agents:
            if agent.nationality == 'Belgium':
                assert agent.activity_locations[activity_manager.as_int('House')][0].typ == 'Belgium'
            if agent.nationality == 'France':
                assert agent.activity_locations[activity_manager.as_int('House')][0].typ == 'France'
            if agent.nationality == 'Germany':
                assert agent.activity_locations[activity_manager.as_int('House')][0].typ == 'Germany'

        for agent in world.agents:
            if agent.nationality != 'Luxembourg':
                assert agent.age >= config['world_factory']['min_age_border_workers']
                assert agent.age <= config['world_factory']['max_age_border_workers']

        for agent in world.agents:
            if agent.activity_locations[activity_manager.as_int('House')][0].typ == 'Care Home':
                assert agent.age >= config['world_factory']['retired_age_limit']

        for location_type in config['locations']:
            assert len(world.locations_for_types(location_type)) > 0

        for location_type in config['world_factory']['deterministic_location_counts']:
            if location_type == 'Primary School':
                assert len(world.locations_for_types(location_type)) == config['world_factory']['deterministic_location_counts'][location_type]*config['world_factory']['num_classes_per_school'][location_type]
            elif location_type == 'Secondary School':
                assert len(world.locations_for_types(location_type)) == config['world_factory']['deterministic_location_counts'][location_type]*config['world_factory']['num_classes_per_school'][location_type]
            else:
                assert len(world.locations_for_types(location_type)) == config['world_factory']['deterministic_location_counts'][location_type]

        occupancy_dict = defaultdict(set)
        for agent in world.agents:
            home = agent.activity_locations[activity_manager.as_int('House')][0]
            occupancy_dict[home].add(agent)
        for home in occupancy_dict:
            if len(occupancy_dict[home]) > 7:
                assert home.typ in ['Care Home', 'Belgium', 'France', 'Germany']

        visite_lux_lux  = world_factory._make_distribution('Visite', 'Luxembourg', 'Luxembourg', 10, 10)
        achats_lux_lux  = world_factory._make_distribution('Achats', 'Luxembourg', 'Luxembourg', 10, 10)
        repas_lux_lux   = world_factory._make_distribution('Repas', 'Luxembourg', 'Luxembourg', 10, 10)
        travail_lux_lux = world_factory._make_distribution('Travail', 'Luxembourg', 'Luxembourg', 10, 10)
        travail_bel_lux = world_factory._make_distribution('Travail', 'Belgique', 'Luxembourg', 10, 10)
        travail_fra_lux = world_factory._make_distribution('Travail', 'France', 'Luxembourg', 10, 10)
        travail_all_lux = world_factory._make_distribution('Travail', 'Allemagne', 'Luxembourg', 10, 10)

        assert abs(sum(visite_lux_lux.values()) - 1.0)  < 1e-9
        assert abs(sum(achats_lux_lux.values()) - 1.0)  < 1e-9
        assert abs(sum(repas_lux_lux.values()) - 1.0)   < 1e-9
        assert abs(sum(travail_lux_lux.values()) - 1.0) < 1e-9
        assert abs(sum(travail_bel_lux.values()) - 1.0) < 1e-9
        assert abs(sum(travail_fra_lux.values()) - 1.0) < 1e-9
        assert abs(sum(travail_all_lux.values()) - 1.0) < 1e-9

        assert world_factory._get_weight(15, visite_lux_lux) == visite_lux_lux[range(10,20)]
        assert world_factory._get_weight(45, achats_lux_lux) == achats_lux_lux[range(50,60)]
        assert world_factory._get_weight(500, travail_fra_lux) == 0

        assert world_factory._get_weight(65, travail_fra_lux) <= 1.0
        assert world_factory._get_weight(17, achats_lux_lux) <= 1.0
        assert world_factory._get_weight(17.434, visite_lux_lux) <= 1.0

        workplace_weights = world_factory._make_work_profile_dictionary(world)
        weights_dict      = {l.typ : workplace_weights[l] for l in list(workplace_weights.keys())}

        for weight in weights_dict.values():
            assert weight > 0

        car_house_dict = defaultdict(set)
        for location in world.locations:
            if location.typ == 'Car' or location.typ == 'House':
                car_house_dict[location.coord].add(location)
        for coord in car_house_dict:
            assert len(car_house_dict[coord]) == 2

    def test_world_factory_large(self):

        config = Config("tests/test_configs/test_config_2.yaml")
        sim_factory = SimulationFactory(config)

        config = sim_factory.config

        # -----------------------------------[ World ]---------------------------------

        # Create the map
        map_factory_class = config['map_factory.__type__']
        map_factory_config = config.subconfig('map_factory')
        map_factory = instantiate_class("abmlux.world.map_factory", map_factory_class,
                                        map_factory_config)
        _map = map_factory.get_map()
        sim_factory.set_map(_map)

        # Create the world, providing it with the map
        world_factory_class = config['world_factory.__type__']
        world_factory_config = config.subconfig('world_factory')
        world_factory = instantiate_class('abmlux.world.world_factory', world_factory_class, sim_factory.map,
                                        sim_factory.activity_manager, world_factory_config)

        world = world_factory.get_world()
        sim_factory.set_world_model(world)

        activity_manager = sim_factory.activity_manager

        # working_dict = defaultdict(set)
        # for agent in world.agents:
        #     work = agent.activity_locations[activity_manager.as_int('Work')][0]
        #     working_dict[work].add(agent)
        # no_workers = []
        # for location in world.locations:
        #     if location not in set(working_dict.keys()):
        #         if location.typ not in ['Belgium', 'France', 'Germany', 'Cemetery', 'Car', 'Outdoor', 'House']:
        #             no_workers.append(location)
        #             print([location.typ, 0])
        # worker_profiles = [[l.typ, len(working_dict[l])] for l in working_dict.keys()]

        def takeFirst(elem):
            return elem[0]
        def takeSecond(elem):
            return elem[1]

        # # sort list with key
        # worker_profiles.sort(reverse=True, key=takeSecond)

        # print(worker_profiles)
        # print(len(list(working_dict.keys())), len(no_workers))

        # school_dict = defaultdict(set)
        # for agent in world.agents:
        #     school = agent.activity_locations[activity_manager.as_int('School')][0]
        #     if agent.age < 4:
        #         assert school.typ == "House"
        #     if agent.age >= 5 and agent.age < 12:
        #         assert school.typ == "Primary School"
        #     if agent.age >= 12:
        #         assert school.typ in ['Secondary School', 'Belgium', 'France', 'Germany', 'Care Home']
        #     if agent.age >= 5 and agent.age < 18:
        #         school_dict[school].add(agent)
        # for school in school_dict:
        #     print(school.typ, len(school_dict[school]))

        activities = ['House', 'Work', 'School', 'Restaurant', 'Outdoor', 'Car', 'Public Transport', 'Shop', 'Medical', 'Place of Worship', 'Indoor Sport', 'Cinema or Theatre', 'Museum or Zoo', 'Visit']
        av_dist_dict = {}
        for activity in activities:
            total_dist = 0
            dist_dict = {}
            for agent in world.agents:
                if agent.nationality == 'Luxembourg':
                    home = agent.activity_locations[activity_manager.as_int('House')][0]
                    if home.typ != 'Care Home':
                        location = agent.activity_locations[activity_manager.as_int(activity)][0]
                        #print(ETRS89_to_WGS84(home.coord), ETRS89_to_WGS84(location.coord))
                        #print(home.coord, location.coord)
                        rnded_dist = (int(home.distance_euclidean(location))//1000)#*100
                        if rnded_dist in dist_dict:
                            dist_dict[rnded_dist] += 1
                        else:
                            dist_dict[rnded_dist] = 1
                        total_dist += home.distance_euclidean(location)
            average_dist = total_dist/len(world.agents)
            av_dist_dict[activity] = average_dist
            # print(home.distance_euclidean(location), 'meters')
            dist_list = [[a,b] for a, b in dist_dict.items()]
            dist_list.sort(key=takeFirst)
            # print('ACTIVITY:', activity)
            # print(dist_list)
        for activity in av_dist_dict:
            if activity in ['House', 'Car']:
                assert av_dist_dict[activity] == 0.0
            else:
                assert av_dist_dict[activity] > 0.0
        # print(av_dist_dict)
