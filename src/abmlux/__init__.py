"""ABMLUX is an agent-based epidemiology model for Luxembourg based on a markov chain."""

import os
import os.path as osp
import sys
import random
import logging
import logging.config

import abmlux.density_model as density_model
import abmlux.network_model as network_model
import abmlux.markov_model as markov_model
from abmlux.simulator import Simulator
from abmlux.reporter import BasicCLIReporter, CSVReporter
from .config import Config
from .activity_manager import ActivityManager
from .serialisation import read_from_disk, write_to_disk

# Support modules
VERSION = "0.1.0"

# Config
MAP_FILENAME                   = 'Density_Map.pickle'
NETWORK_FILENAME               = "Network.pickle"
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
    density = density_model.read_density_model_jrc(config.filepath('population_distribution_fp'),
                                                   config['country_code'])

    # ############## Output Data ##############
    # Handle output to write to disk if required
    write_to_disk(density, osp.join(config.filepath('working_dir', True), MAP_FILENAME))


def build_network(config):
    """Build a network of locations and agents based on the population density"""

    # ------------------------------------------------[ 2 ]------------------------------------
    # Step two: build network model

    # ############## Input Data ##############
    # The density matrix contructed by the file DensityModel is now loaded:
    density = read_from_disk(osp.join(config.filepath('working_dir'), MAP_FILENAME))

    # ############## Run Stage ##############
    network = network_model.build_network_model(config, density)

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

    # ------------------------------------------------[ 3 ]------------------------------------
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

    # ------------------------------------------------[ 4 ]------------------------------------
    # Step four: simulate
    # ############## Input Data ##############
    network                = read_from_disk(osp.join(config.filepath('working_dir', True),\
                                            NETWORK_FILENAME))
    activity_transitions   = read_from_disk(osp.join(config.filepath('working_dir', True),\
                                            TRANSITION_MATRIX_FILENAME))

    # Reporters
    # TODO: make configurable
    reporters = [BasicCLIReporter(), CSVReporter("/tmp/out.csv")]

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
    random.seed(config['random_seed'])
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
