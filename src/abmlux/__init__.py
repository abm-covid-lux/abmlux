


import os, sys
import random

# Needed for save/load code (TODO: move this out of this module)
import os.path as osp
import pickle
import pandas as pd

from .config import Config

# Main functions
from .density_model import read_density_model_jrc
from .network_model import build_network_model
from .markov_model import build_markov_model
from .abm import run_model

# Support modules

VERSION = "0.1.0"
PICKLE_RECURSION_LIMIT = 100000  # Allows export of highly nested data


# Config
MAP_FILENAME                   = 'Density_Map.pickle'
NETWORK_FILENAME               = "Network.pickle"
INITIAL_DISTRIBUTIONS_FILENAME = 'Initial_Activities.pickle'
TRANSITION_MATRIX_FILENAME     = 'Activity_Transition_Matrix.pickle'
AGENT_COUNTS_FILENAME          = "Agent_Counts.csv"






def load_pop_density(config):


    # ------------------------------------------------[ 1 ]------------------------------------
    # Step one: process density information
    # ############## Input Data ##############

    # ############## Run Stage ##############
    density = read_density_model_jrc(config.filepath('population_distribution_fp'), config['country_code'])

    # ############## Output Data ##############
    # Handle output to write to disk if required
    write_to_disk(density, osp.join(config.filepath('working_dir', True), MAP_FILENAME))


def build_network(config):


    # ------------------------------------------------[ 2 ]------------------------------------
    # Step two: build network model

    # ############## Input Data ##############
    # The density matrix contructed by the file DensityModel is now loaded:
    density = read_from_disk(osp.join(config.filepath('working_dir'), MAP_FILENAME))

    # ############## Run Stage ##############
    network = build_network_model(config, density)

    # ############## Output Data ##############
    write_to_disk(network, osp.join(config.filepath('working_dir', True), NETWORK_FILENAME))


def build_markov(config):

    # ------------------------------------------------[ 3 ]------------------------------------
    # Step three: build markov model
    # ############## Input Data #############

    # ############## Run Stage ##############
    initial_activity_distributions, activity_transition_matrix = build_markov_model(config)


    # ############## Output Data ##############
    write_to_disk(initial_activity_distributions, osp.join(config.filepath('working_dir', True), INITIAL_DISTRIBUTIONS_FILENAME))
    write_to_disk(activity_transition_matrix, osp.join(config.filepath('working_dir', True), TRANSITION_MATRIX_FILENAME))


def run_sim(config):


    # ------------------------------------------------[ 4 ]------------------------------------
    # Step four: simulate
    # ############## Input Data ##############
    network                        = read_from_disk(osp.join(config.filepath('working_dir', True), NETWORK_FILENAME))
    initial_activity_distributions = read_from_disk(osp.join(config.filepath('working_dir', True), INITIAL_DISTRIBUTIONS_FILENAME))
    activity_transition_matrix     = read_from_disk(osp.join(config.filepath('working_dir', True), TRANSITION_MATRIX_FILENAME))

    # ############## Run Stage ##############
    health_status_by_time = run_model(config, network, initial_activity_distributions, activity_transition_matrix)

    # ############## Output Data ##############
    agent_counts_filename = osp.join(config.filepath('results_dir', True), AGENT_COUNTS_FILENAME)
    print(f"Writing agent counts to {agent_counts_filename}...")
    health_status_by_time = pd.DataFrame(health_status_by_time)
    health_status_by_time.to_csv(agent_counts_filename)











STAGES = [load_pop_density, build_network, build_markov, run_sim]
def main():
    print(f"ABMLUX {VERSION}")

    # Check the path to the config
    if len(sys.argv) < 2:
        print(f"USAGE: {sys.argv[0]} path/to/scenario/config.yml [STAGE,STAGE,STAGE]")
        print(f"")
        print(f"EG: {sys.argv[0]} Scenarios/Luxembourg/config.yaml 1,2")
        sys.exit(1)


    # System config/setup
    # TODO: can we do exponential backoff on this?
    config = Config(sys.argv[1])
    sys.setrecursionlimit(PICKLE_RECURSION_LIMIT)
    random.seed(config['random_seed'])


    # Figure out what we're doing
    if len(sys.argv) > 2:
        print(f"Running only some stages.  Will fail if you haven't got prerequisite data from earlier runs.")
        stages = [STAGES[int(x) - 1] for x in sys.argv[2].split(",")]
    else:
        stages = STAGES
    print(f"Running modelling stages:")
    for i, stage in enumerate(stages):
        print(f" ({i+1}) -- {stage.__name__}")


    # Do it
    for i, stage in enumerate(stages):
        print(f"\n[{i+1}/{len(stages)}] {stage.__name__}")
        print(f"")

        stage(config)


# ===============================================================================================
# Data Access utils
#
# TODO: move these elsewhere.

def write_to_disk(obj, output_filename):
    print(f"Writing to {output_filename}...")
    with open(output_filename, 'wb') as fout:
        pickle.dump(obj, fout)


def read_from_disk(input_filename):
    print(f'Reading data from {input_filename}...')
    with open(input_filename, 'rb') as fin:
        payload = pickle.load(fin)

    return payload


