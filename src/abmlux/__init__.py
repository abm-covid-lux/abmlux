


import os, sys

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
MAP_FILENAME                   = 'Density_Map.csv'
NETWORK_FILENAME               = "Network.pickle"
INITIAL_DISTRIBUTIONS_FILENAME = 'Initial_Activities.pickle'
TRANSITION_MATRIX_FILENAME     = 'Activity_Transition_Matrix.pickle'
AGENT_COUNTS_FILENAME          = "agent_counts.csv"


def main():
    print(f"ABMLUX {VERSION}")

    # Check the path to the config
    if len(sys.argv) < 2:
        print(f"USAGE: {sys.argv[0]} path/to/scenario/config.yml")
        sys.exit(1)

    # System config/setup
    #
    # TODO: can we do exponential backoff on this?
    sys.setrecursionlimit(PICKLE_RECURSION_LIMIT)


    # ------------------------------------------------[ 1 ]------------------------------------
    # Step one: process density information
    # ############## Input Data ##############
    config = Config(sys.argv[1])

    # ############## Run Stage ##############
    density = read_density_model_jrc(config.filepath('population_distribution_fp'), config['country_code'])

    # ############## Output Data ##############
    # Handle output to write to disk if required
    write_to_disk(density, osp.join(config.filepath('working_dir', True), MAP_FILENAME))





    # ------------------------------------------------[ 2 ]------------------------------------
    # Step two: build network model

    # ############## Input Data ##############
    # The density matrix contructed by the file DensityModel is now loaded:
    density = read_from_disk(osp.join(config.filepath('working_dir'), MAP_FILENAME))

    # ############## Run Stage ##############
    network = build_network_model(config, density)

    # ############## Output Data ##############
    write_to_disk(network, osp.join(config.filepath('working_dir', True), NETWORK_FILENAME))




    # ------------------------------------------------[ 3 ]------------------------------------
    # Step three: build markov model
    # ############## Input Data #############

    # ############## Run Stage ##############
    initial_activity_distributions, activity_transition_matrix = build_markov_model(config)


    # ############## Output Data ##############
    write_to_disk(initial_activity_distributions, osp.join(config.filepath('working_dir', True), INITIAL_DISTRIBUTIONS_FILENAME))
    write_to_disk(activity_transition_matrix, osp.join(config.filepath('working_dir', True), TRANSITION_MATRIX_FILENAME))





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



    print(f"Done.")

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


