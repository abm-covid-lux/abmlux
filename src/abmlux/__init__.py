"""ABMLUX is an agent-based epidemiology model for Luxembourg based on a markov chain."""

import os
import os.path as osp
import sys
import logging
import logging.config
import traceback

from abmlux.location_model.simple_random import SimpleRandomLocationModel
import abmlux.random_tools as random_tools
import abmlux.density_model as density_model
import abmlux.network_model as network_model
from abmlux.utils import instantiate_class
from abmlux.messagebus import MessageBus
from abmlux.sim_state import SimulationState, SimulationPhase
from abmlux.simulator import Simulator
from abmlux.disease.compartmental import CompartmentalModel
from abmlux.activity.tus_survey import TUSMarkovActivityModel

import abmlux.tools as tools

from abmlux.version import VERSION
from abmlux.config import Config
from abmlux.serialisation import read_from_disk, write_to_disk


# Global module log
log = logging.getLogger()


def load_map(state):
    """Load population density and build a density model based on the description."""

    config = state.config
    state.map = density_model.read_density_model_jrc(state.prng,
                                                     config.filepath('map.population_distribution_fp'),
                                                     config['map.country_code'],
                                                     config['map.res_fact'],
                                                     config['map.normalize_interpolation'],
                                                     config.filepath('map.shapefilename'),
                                                     config['map.shapefile_coordinate_system'])

def build_network(state):
    """Build a network of locations and agents based on the population density"""

    state.network = network_model.build_network_model(state.prng, state.config, state.map)


def build_markov(state):
    """Build a markov model of activities to transition through"""

    state.activity_model = TUSMarkovActivityModel(state.prng, state.config, state.bus, \
                                                  state.activity_manager)

def disease_model(state):
    """Set up disease model."""

    # TODO: make this dynamic from the config file (like reporters)
    disease_model_class  = state.config['disease_model.__type__']
    disease_model_config = state.config['disease_model']
    disease_model = instantiate_class("abmlux.disease", disease_model_class, state.prng,\
                                      disease_model_config, state.bus, state)

    state.disease = disease_model

def location_model(state):
    """set up location model"""

    state.location_model = SimpleRandomLocationModel(state.prng, state.config, state.bus, \
                                                     state.activity_manager)

def intervention_setup(state):
    """Set up interventions"""

    # Reporters
    interventions = {}
    intervention_schedules = {}
    for intervention_id, intervention_config in state.config["interventions"].items():

        # Extract keys from the intervention config
        intervention_class    = intervention_config['__type__']

        log.info("Creating intervention %s of type %s...", intervention_id, intervention_class)
        initial_enabled = False if '__enabled__' in intervention_config \
                                                 and not intervention_config['__enabled__']\
                                else True
        new_intervention = instantiate_class("abmlux.interventions", intervention_class, \
                                             state.prng, intervention_config, \
                                             state.clock, state.bus, state, initial_enabled)

        interventions[intervention_id]           = new_intervention
        intervention_schedules[new_intervention] = intervention_config['__schedule__']

    # Save for later use by the sims
    state.interventions          = interventions
    state.intervention_schedules = intervention_schedules

    # Initialise internal state of the intervention object, and allow it to
    # modify the network if needed
    for intervention_id, intervention in state.interventions.items():
        log.info("Initialising intervention %s...", intervention_id)
        intervention.initialise_agents(state.network)

def run_sim(state):
    """Run the agent-based model itself"""

    # ------------------------------------------------[ 5 ]------------------------------------
    # TODO: move the bulk of this logic into the simulator object itself

    # Reporters
    reporters = []
    for spec in state.config['reporters']:
        fqclass_name = list(spec.keys())[0]
        params = spec[fqclass_name]

        log.info("Creating reporter %s...", fqclass_name)

        reporter = instantiate_class("abmlux.reporters", fqclass_name, **params)

        reporters.append(reporter)

    # ############## Run Stage ##############
    sim = Simulator(state, reporters)

    sim.run()



PHASES = {SimulationPhase.BUILD_MAP:         load_map,
          SimulationPhase.BUILD_NETWORK:     build_network,
          SimulationPhase.BUILD_ACTIVITIES:  build_markov,
          SimulationPhase.ASSIGN_DISEASE:    disease_model,
          SimulationPhase.LOCATION_MODEL:    location_model,
          SimulationPhase.INIT_INTERVENTION: intervention_setup,
          SimulationPhase.RUN_SIM:           run_sim}
def main():
    """Main ABMLUX entry point"""
    print(f"ABMLUX {VERSION}")

    # Check the path to the config
    if len(sys.argv) < 2:
        print(f"USAGE: {sys.argv[0]} state.abm [STAGE,STAGE,STAGE [path/to/config.yml]]")
        print("")
        print(f"EG: {sys.argv[0]} Scenarios/Luxembourg/config.yaml 1,2")
        sys.exit(1)

    # Determine if we're loading a simulation state, or the config file to create one
    # Python's tenets say we should ask for forgiveness, so let's do it this way:
    #
    # TODO: make this more explicit to the user, perhaps by changing the way the command line
    #       'phases' work

    state_filename = sys.argv[1]
    try:
        print(f"Attempting to read state from {state_filename}...")
        state = read_from_disk(state_filename)
        write_to_disk(state, state_filename)
        config = state.config

        # If a config path is given, force the config to change
        if len(sys.argv) > 3:
            print(f"WARNING: Overriding config using file at {sys.argv[3]}.")
            state.config = Config(sys.argv[3])

    # pylint disable=bare-except
    except:
        if len(sys.argv) <= 3:
            print("Error: Statefile doesn't exist yet, but no config has been given to create one")
            sys.exit(1)

        print(f"Creating new statefile at {state_filename} using config at {sys.argv[3]}...")
        config = Config(sys.argv[3])
        state = SimulationState(config)

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
    log.info("  Dirty?: %s", state.dirty)
    # Show progress
    log.info("  Phases completed:")
    for phase in list(SimulationPhase):
        log.info("    %i. %s: %s", int(phase)+1, phase.name, state.is_phase_complete(phase))

    if state.dirty:
        log.warning(("State is marked as dirty.  This means the simulation phases have not run"
                     " in-order, and the PRNG state is not replicable.  To solve, re-run all"
                     " stages."))

    if state.finished:
        log.warning(("State is marked as finished.  Any further changes will overwrite"
                     " information used when generating results, invalidating them."
                     "  Unless you know this process will not change the simulation state,"
                     " recommend starting again and re-running all phases in sequence."))

    if state.abmlux_version != VERSION:
        log.warning(("Current ABMLUX version (%s) differs from the version used to create"
                     " the simulation state (%s).  This will probably lead to errors,"
                     " and will invalidate the output even if no errors are visible"))

    # Figure out what we're doing
    if len(sys.argv) > 2:
        phases = {SimulationPhase(int(x)-1): PHASES[int(x) - 1] for x in sys.argv[2].split(",")}
    else:
        phases = PHASES

    log.info("Running modelling phases:")
    for name, phase_func in phases.items():
        log.info(" (%i) -- %s", int(name) + 1, name.name)

    # Do it
    i = 0
    for name, phase_func in phases.items():
        i += 1
        log.info("Running phase %i (%i/%i) %s", int(name), i, len(phases), name.name)

        state.set_phase(name)

        try:
            phase_func(state)
        except: # pylint: disable=C0103,W0702
            e = sys.exc_info()[0]
            log.fatal("Fatal error in phase %i (%s): %s", i, name.name, e)
            log.error(traceback.format_exc())
            log.fatal("Shutting down to prevent further errors.")
            sys.exit(1)

        state.set_phase_complete(name)
        write_to_disk(state, state_filename)


TOOLS = ["plot_locations", "plot_activity_routines", "export_locations_kml", "join_images"]
def main_tools():
    # FIXME: broken until the state code is ported here!
    """Entry point for AMBLUX reporting/analysis tools"""
    print(f"ABMLUX {VERSION}")

    # Check the path to the config
    if len(sys.argv) < 3:
        print(f"USAGE: {sys.argv[0]} simulation_state.abm tool_name [options]")
        print("")
        print(f"EG: {sys.argv[0]} simulation_state.abm plot_locations")
        print("")
        print("List of tools:")
        for tool in TOOLS:
            mod = tools.get_tool_module(tool)
            print(f" - {tool}: {mod.DESCRIPTION}")
        print("")
        sys.exit(1)

    # System config/setup
    state = read_from_disk(sys.argv[1])
    logging.config.dictConfig(state.config['logging'])

    # Command
    command = sys.argv[2]
    if command not in TOOLS:
        log.error("Tool not found: %s", command)
        sys.exit(1)
    command = getattr(tools.get_tool_module(command), "main")

    parameters = sys.argv[3:]
    log.info("Parameters for tool: %s", parameters)

    # Run the thing.
    try:
        command(state, *parameters)
    except: # pylint: disable=C0103,W0702
        e = sys.exc_info()[0]
        log.fatal("Fatal error in tool execution '%s' with params '%s': %s",
                  command.__name__, parameters, e)
        log.error(traceback.format_exc())
        sys.exit(1)
