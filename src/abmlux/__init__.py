"""ABMLUX is an agent-based epidemiology model for Luxembourg based on a markov chain."""

import os
import os.path as osp
import sys
import logging
import logging.config
import traceback
import argparse

from abmlux.movement_model.simple_random import SimpleRandomMovementModel
from abmlux.random_tools import Random
from abmlux.utils import instantiate_class, remove_dunder_keys
from abmlux.messagebus import MessageBus
from abmlux.sim_state import SimulationFactory
from abmlux.simulator import Simulator
from abmlux.disease_model.compartmental import CompartmentalModel
from abmlux.activity.tus_survey import TUSMarkovActivityModel
from abmlux.telemetry import TelemetryClient

import abmlux.tools as tools

from abmlux.version import VERSION
from abmlux.config import Config
from abmlux.serialisation import read_from_disk, write_to_disk


# Global module log
log = logging.getLogger()


def build_model(sim_factory):

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
    world_factory = instantiate_class("abmlux.world.world_factory", world_factory_class, sim_factory.map,
                                      sim_factory.activity_manager, world_factory_config)
    world = world_factory.get_world()
    sim_factory.set_world_model(world)


    # -----------------------------------[ Components ]---------------------------------

    # Disease model
    disease_model_class  = config['disease_model.__type__']
    disease_model_config = config.subconfig('disease_model')
    disease_model = instantiate_class("abmlux.disease_model", disease_model_class,
                                      disease_model_config)
    sim_factory.set_disease_model(disease_model)

    # Activity model
    activity_model_class = config['activity_model.__type__']
    activity_model_config = config.subconfig('activity_model')
    activity_model = instantiate_class("abmlux.activity", activity_model_class,
                                       activity_model_config, sim_factory.activity_manager)
    sim_factory.set_activity_model(activity_model)

    # How agents move around locations
    movement_model_class = config['movement_model.__type__']
    movement_model_config = config.subconfig('movement_model')
    movement_model = instantiate_class("abmlux.movement_model", movement_model_class,
                                       movement_model_config)
    sim_factory.set_movement_model(movement_model)

    # Interventions
    for intervention_id, intervention_config in config["interventions"].items():

        # Extract keys from the intervention config
        intervention_class    = intervention_config['__type__']

        log.info("Creating intervention %s of type %s...", intervention_id, intervention_class)
        initial_enabled = False if '__enabled__' in intervention_config \
                                                 and not intervention_config['__enabled__']\
                                else True
        new_intervention = instantiate_class("abmlux.interventions", intervention_class, \
                                             intervention_config, initial_enabled)

        sim_factory.add_intervention(intervention_id, new_intervention)
        sim_factory.add_intervention_schedule(new_intervention, intervention_config['__schedule__'])



def build_reporters(config):

    reporters = []
    for reporter_class, reporter_config in config['reporters'].items():
        log.info(f"Creating reporter '{reporter_class}'...")

        rep = instantiate_class("abmlux.reporters", reporter_class, config['telemetry.host'],
                                config['telemetry.port'], Config(_dict=reporter_config))
        reporters.append(rep)

    return reporters




SIM_FACTORY_FILENAME = "state.abm"
def main():
    """Main ABMLUX entry point"""
    print(f"ABMLUX {VERSION}")

    # System config/setup
    if osp.isfile(SIM_FACTORY_FILENAME):
        sim_factory = SimulationFactory.from_file(SIM_FACTORY_FILENAME)
        logging.config.dictConfig(sim_factory.config['logging'])
        log.warning("Existing factory loaded from %s", SIM_FACTORY_FILENAME)
    else:
        config = Config(sys.argv[1])
        sim_factory = SimulationFactory(config)
        logging.config.dictConfig(sim_factory.config['logging'])

        # Summarise the sim_factory
        log.info("State info:")
        log.info("  Run ID: %s", sim_factory.run_id)
        log.info("  ABMLUX version: %s", sim_factory.abmlux_version)
        log.info("  Created at: %s", sim_factory.created_at)
        log.info("  Activity Model: %s", sim_factory.activity_model)
        log.info("  Map: %s", sim_factory.map)
        log.info("  World: %s", sim_factory.world)
        log.info("  PRNG seed: %i", sim_factory.config['random_seed'])

        build_model(sim_factory)
        sim_factory.to_file(SIM_FACTORY_FILENAME)

    reporters = build_reporters(sim_factory.config)

    log.info("Starting %s reporters...", len(reporters))
    for reporter in reporters:
        reporter.start()

    # ############## Run ##############
    sim = sim_factory.new_sim()
    sim.run()

    log.info("Requesting that reporters finish...")
    for reporter in reporters:
        reporter.stop()

    # Wait for all reporters to complete
    log.info("Waiting for reporters to finish...")
    for reporter in reporters:
        reporter.join()
    log.info("Simulation Finished successfully.")


from abmlux.reporters import kill_on_zmq_event

def main_reporter():
    """Listen to the Telemetry and dump to the terminal"""


    parser = argparse.ArgumentParser(description='Run the ABMLUX reporter modules')
    parser.add_argument("-t", "-host", dest='host', action="store", type=str, default="127.0.0.1",
                        help="Hostname of the telemetry endpoint")
    parser.add_argument("-p", "-port", dest='port', action="store", type=int, default=4567,
                        help="Port of the telemetry endpoint")
    parser.add_argument("-c", "-config", dest='config', action="store", type=str, default=None,
                        help="Filename of config file to configure reporters")
    parser.add_argument("-q", "-quit", dest='quit', action="store_true", default=False,
                        help="Quit at the end of the next simulation.")
    parser.add_argument("reporter", nargs="+", help="Reporter(s) to run.")

    args = parser.parse_args()

    # Load config if specified
    if args.config is None:
        config = Config(_dict={})
    else:
        config = Config(args.config)

    reporters = []
    for reporter_class in args.reporter:
        print(f"Creating reporter '{reporter_class}'...")

        if 'reporters' in config and reporter_class in config['reporters']:
            reporter_config = Config(_dict=config['reporters'][reporter_class])
        else:
            reporter_config = Config(_dict={})

        rep = instantiate_class("abmlux.reporters", reporter_class, args.host, args.port,
                                reporter_config)
        reporters.append(rep)

    print(f"Starting {len(reporters)} reporters...")
    for reporter in reporters:
        reporter.start()
    print("Done")

    print("Waiting for reporters to finish up.  Now is a good time to start your simulator.")

    if args.quit:
        print(f"Will kill all reporters at the end of the simulation")
        kill_on_zmq_event(args.host, args.port, 'simulation.end', reporters)

    # Wait for all to complete
    for reporter in reporters:
        reporter.join()
    print("Done.  Have a nice day!")
