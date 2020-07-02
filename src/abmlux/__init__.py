


import os, sys
from .config import Config

# Main functions
from .density_model import build_density_model
from .network_model import build_network_model
from .markov_model import build_markov_model
from .abm import run_model

# Support modules

VERSION = "0.1.0"

def main():
    print(f"ABMLUX {VERSION}")

    # Check the path to the config
    if len(sys.argv) < 2:
        print(f"USAGE: {sys.argv[0]} path/to/scenario/config.yml")
        sys.exit(1)

    config = Config(sys.argv[1])


    # Step one: process density information
    build_density_model(config)

    # Step two: build network model
    build_network_model(config)

    # Step three: build markov model
    build_markov_model(config)

    # Step four: simulate
    run_model(config)


    print(f"Done.")



