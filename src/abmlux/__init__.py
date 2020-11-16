"""ABMLUX is an agent-based epidemiology model for Luxembourg based on a markov chain."""

import os
import os.path as osp
import sys
import logging
import logging.config
import traceback

from abmlux.location_model.simple_random import SimpleRandomLocationModel
import abmlux.density_model as density_model
import abmlux.network_model as network_model
from abmlux.random_tools import Random
from abmlux.utils import instantiate_class
from abmlux.messagebus import MessageBus
from abmlux.sim_state import SimulationFactory
from abmlux.simulator import Simulator
from abmlux.disease.compartmental import CompartmentalModel
from abmlux.activity.tus_survey import TUSMarkovActivityModel

import abmlux.tools as tools

from abmlux.version import VERSION
from abmlux.config import Config
from abmlux.serialisation import read_from_disk, write_to_disk


# Global module log
log = logging.getLogger()



def build_model(state):

    # FIXME: delete this
    prng = Random()

    config = state.config
    state.add_map(density_model.read_density_model_jrc(prng,
                                                     config.filepath('map.population_distribution_fp'),
                                                     config['map.country_code'],
                                                     config['map.res_fact'],
                                                     config['map.normalize_interpolation'],
                                                     config.filepath('map.shapefilename'),
                                                     config['map.shapefile_coordinate_system']))

    """Build a network of locations and agents based on the population density"""
    state.add_network_model(network_model.build_network_model(prng, config, state.map))


    """Build a markov model of activities to transition through"""
    state.add_activity_model(TUSMarkovActivityModel(config, state.activity_manager))

    """Set up disease model."""
    disease_model_class  = config['disease_model.__type__']
    disease_model_config = config['disease_model']
    state.add_disease_model(instantiate_class("abmlux.disease", disease_model_class, disease_model_config))

    """set up location model"""
    state.add_location_model(SimpleRandomLocationModel(config))

    """Set up interventions"""
    # Reporters
    for intervention_id, intervention_config in config["interventions"].items():

        # Extract keys from the intervention config
        intervention_class    = intervention_config['__type__']

        log.info("Creating intervention %s of type %s...", intervention_id, intervention_class)
        initial_enabled = False if '__enabled__' in intervention_config \
                                                 and not intervention_config['__enabled__']\
                                else True
        new_intervention = instantiate_class("abmlux.interventions", intervention_class, \
                                             intervention_config, initial_enabled)

        state.add_intervention(intervention_id, new_intervention)
        state.add_intervention_schedule(new_intervention, intervention_config['__schedule__'])

    # Initialise internal state of the intervention object, and allow it to
    # modify the network if needed
    #for intervention_id, intervention in state.interventions.items():
    #    log.info("Initialising intervention %s...", intervention_id)
    #    intervention.initialise_agents(state.network)

    """Run the agent-based model itself"""
    # ------------------------------------------------[ 5 ]------------------------------------
    # TODO: move the bulk of this logic into the simulator object itself
    # Reporters
    #reporters = []
    #for spec in config['reporters']:
    #    fqclass_name = list(spec.keys())[0]
    #    params = spec[fqclass_name]
#
#        log.info("Creating reporter %s...", fqclass_name)
#
#        reporter = instantiate_class("abmlux.reporters", fqclass_name, state.bus, **params)
#        reporters.append(reporter)


def main():
    """Main ABMLUX entry point"""
    print(f"ABMLUX {VERSION}")

    state_filename = sys.argv[1]
    print(f"Creating new statefile at {state_filename} using config at {sys.argv[2]}...")
    config = Config(sys.argv[2])
    state = SimulationFactory(config)

    # System config/setup
    logging.config.dictConfig(state.config['logging'])

    # Summarise the state
    log.info("State info:")
    log.info("  Run ID: %s", state.run_id)
    log.info("  ABMLUX version: %s", state.abmlux_version)
    log.info("  Created at: %s", state.created_at)
    log.info("  Simulation N: %i", state.config['n'])
    log.info("  Activity Model: %s", state.activity_model)
    log.info("  Map: %s", state.map)
    log.info("  Network: %s", state.network)
    log.info("  PRNG seed: %i", state.config['random_seed'])

    build_model(state)

    # ############## Run ##############
    sim = state.new_sim()
    sim.run()
