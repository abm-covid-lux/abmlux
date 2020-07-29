"""ABMLUX is an agent-based epidemiology model for Luxembourg based on a markov chain."""

import os
import os.path as osp
import sys
import logging
import logging.config
import importlib

import abmlux.random_tools as random_tools
import abmlux.density_model as density_model
import abmlux.network_model as network_model
import abmlux.markov_model as markov_model
from abmlux.simulator import Simulator

import abmlux.tools as tools

from .version import VERSION
from .config import Config
from .activity_manager import ActivityManager
from .serialisation import read_from_disk, write_to_disk

# Config
MAP_FILENAME                   = 'Density_Map.pickle'
NETWORK_FILENAME               = 'Network.pickle'
INITIAL_DISTRIBUTIONS_FILENAME = 'Activity Distributions.pickle'
TRANSITION_MATRIX_FILENAME     = 'Activity Transitions.pickle'
AGENT_COUNTS_FILENAME          = "Agent_Counts.csv"


# Global module log
log = logging.getLogger()


def load_pop_density(config):
    """Load population density and build a density model based on the description."""

    # ------------------------------------------------[ 1 ]------------------------------------
    # Step one: process density information
    # ############## Input Data ##############

    # ############## Run Stage ##############
    density_map = density_model.read_density_model_jrc(config.filepath('map.population_distribution_fp'),
                                                       config['map.country_code'], config['map.res_fact'],
                                                       config['map.normalize_interpolation'],
                                                       config.filepath('map.shapefilename'),
                                                       config['map.shapefile_coordinate_system'])

    # ############## Output Data ##############
    # Handle output to write to disk if required
    write_to_disk(density_map, osp.join(config.filepath('working_dir', True), MAP_FILENAME))


def build_network(config):
    """Build a network of locations and agents based on the population density"""

    # ------------------------------------------------[ 2 ]------------------------------------
    # Step two: build network model

    # ############## Input Data ##############
    # The density matrix contructed by the file density_model is now loaded:
    density_map = read_from_disk(osp.join(config.filepath('working_dir'), MAP_FILENAME))

    # ############## Run Stage ##############
    network = network_model.build_network_model(config, density_map)

    # ############## Output Data ##############
    write_to_disk(network, osp.join(config.filepath('working_dir', True), NETWORK_FILENAME))


def build_markov(config):
    """Build a markov model of activities to transition through"""

    # ------------------------------------------------[ 3 ]------------------------------------
    # Step three: build markov model
    # ############## Input Data #############
    activity_manager = ActivityManager(config['activities'])

    # ############## Run Stage ##############
    activity_distributions, activity_transitions = \
            markov_model.build_markov_model(config, activity_manager)


    # ############## Output Data ##############
    write_to_disk(activity_distributions, osp.join(config.filepath('working_dir', True),\
                  INITIAL_DISTRIBUTIONS_FILENAME))
    write_to_disk(activity_transitions, osp.join(config.filepath('working_dir', True),\
                  TRANSITION_MATRIX_FILENAME))



def assign_activities(config):
    """Assign activities to the agents on the network, creating an initial condition for the
    sim"""

    # ------------------------------------------------[ 4 ]------------------------------------
    # ############## Input Data #############
    network                = read_from_disk(osp.join(config.filepath('working_dir', True),\
                                            NETWORK_FILENAME))
    activity_distributions = read_from_disk(osp.join(config.filepath('working_dir', True),\
                                            INITIAL_DISTRIBUTIONS_FILENAME))

    # ############## Run Stage ##############
    network = network_model.assign_activities(config, network, activity_distributions)


    # ############## Output Data ##############
    write_to_disk(network, osp.join(config.filepath('working_dir', True), NETWORK_FILENAME))


def run_sim(config):
    """Run the agent-based model itself"""

    # ------------------------------------------------[ 5 ]------------------------------------
    # Step four: simulate
    # ############## Input Data ##############
    network                = read_from_disk(osp.join(config.filepath('working_dir', True),\
                                            NETWORK_FILENAME))
    activity_transitions   = read_from_disk(osp.join(config.filepath('working_dir', True),\
                                            TRANSITION_MATRIX_FILENAME))

    # Reporters
    reporters = []
    for spec in config['reporters']:
        fqclass_name = list(spec.keys())[0]
        params = spec[fqclass_name]

        module_name = "abmlux.reporters." + ".".join(fqclass_name.split(".")[:-1])
        class_name  = fqclass_name.split(".")[-1]

        log.debug("Dynamically loading class '%s' from module name '%s'", module_name, class_name)
        mod = importlib.import_module(module_name)
        cls = getattr(mod, class_name)

        log.debug("Instantiating class %s with parameters %s", cls, params)
        reporter = cls(**params)
        reporters.append(reporter)

    # ############## Run Stage ##############
    sim = Simulator(config, network, activity_transitions, reporters)
    sim.run()






STAGES = [load_pop_density, build_network, build_markov, assign_activities, run_sim]
def main():
    """Main ABMLUX entry point"""
    print(f"ABMLUX {VERSION}")

    # Check the path to the config
    if len(sys.argv) < 2:
        print(f"USAGE: {sys.argv[0]} path/to/scenario/config.yml [STAGE,STAGE,STAGE]")
        print("")
        print(f"EG: {sys.argv[0]} Scenarios/Luxembourg/config.yaml 1,2")
        sys.exit(1)


    # System config/setup
    config = Config(sys.argv[1])
    random_tools.random_seed(config['random_seed'])
    logging.config.dictConfig(config['logging'])

    # Figure out what we're doing
    if len(sys.argv) > 2:
        log.warning("Running only some stages.  Will fail if you haven't got prerequisite data"
                    "from earlier runs.")
        stages = [STAGES[int(x) - 1] for x in sys.argv[2].split(",")]
    else:
        stages = STAGES
    log.info("Running modelling stages:")
    for i, stage in enumerate(stages):
        log.info(" (%i) -- %s", i+1, stage.__name__)

    # Do it
    for i, stage in enumerate(stages):
        log.info("[%i/%i] %s", i+1, len(stages), stage.__name__)

        stage(config)


TOOLS = ["plot_locations", "plot_activity_routines", "export_locations_kml", "join_images"]
def main_tools():
    """Encry point for AMBLUX reporting/analysis tools"""
    print(f"ABMLUX {VERSION}")

    # Check the path to the config
    if len(sys.argv) < 3:
        print(f"USAGE: {sys.argv[0]} path/to/scenario/config.yml tool_name [options]")
        print("")
        print(f"EG: {sys.argv[0]} Scenarios/Luxembourg/config.yaml plot_locations")
        print("")
        print("List of tools:")
        for tool in TOOLS:
            mod = tools.get_tool_module(tool)
            print(f" - {tool}: {mod.DESCRIPTION}")
        print("")
        sys.exit(1)


    # System config/setup
    config = Config(sys.argv[1])
    random_tools.random_seed(config['random_seed'])
    logging.config.dictConfig(config['logging'])

    # Command
    command = sys.argv[2]
    if command not in TOOLS:
        log.error(f"Tool not found: {command}")
        sys.exit(1)
    command = getattr(tools.get_tool_module(command), "main")

    parameters = sys.argv[3:]
    log.info(f"Parameters for tool: {parameters}")

    # Run the thing.
    command(config, *parameters)
