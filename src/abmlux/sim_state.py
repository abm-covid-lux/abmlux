"""Represents the simulation state.  Is built gradually by the various model stages, ands then
ingested by the simulator as it runs."""

import logging
import uuid
import random
from datetime import datetime
from enum import IntEnum

from .version import VERSION
from .activity_manager import ActivityManager

log = logging.getLogger("sim_state")

class SimulationPhase(IntEnum):
    """Represents the current stage of the simulation"""

    BUILD_MAP         = 0
    BUILD_NETWORK     = 1
    BUILD_ACTIVITIES  = 2
    ASSIGN_ACTIVITIES = 3
    ASSIGN_DISEASE    = 4
    INIT_INTERVENTION = 5
    RUN_SIM           = 6


class SimulationState:

    def __init__(self, config):
        """Create a new state object.

        This object will get gradually built during the setup phase, then
        used during the simulation, after being 'sealed'"""

        self.abmlux_version = VERSION
        self.created_at     = datetime.now()
        self.run_id         = uuid.uuid4().hex
        self.phase          = SimulationPhase(0)
        self.phases         = [False] * len(list(SimulationPhase))
        self.dirty          = False
        self.finished       = False
        self.prng           = random.Random()
        self.reseed_prng(config['random_seed'])

        log.info("Simulation state created at %s with ID=%s", self.created_at, self.run_id)

        self.config                 = config
        self.activity_manager       = ActivityManager(config['activities'])
        self.map                    = None
        self.network                = None
        self.activity_distributions = None
        self.activity_transitions   = None
        self.disease                = None
        self.intervention           = None

    def set_phase_complete(self, phase):
        """Reports that a phase has been completed"""
        self.phases[phase] = True

        # Check to see if this was the last phase
        for previous_phase in list(SimulationPhase):
            if not self.is_phase_complete(previous_phase):
                return
        self.finished = True

    def is_phase_complete(self, phase):
        """Returns whether or not a phase has been completed"""
        return self.phases[phase]

    def set_dirty(self):
        """Set the dirty flag to indicate that the state has been run out-of-order somehow"""
        self.dirty = True

    def _get_prng_state(self):
        """Return internal PRNG state for saving."""
        return self.prng.getstate()

    def _set_prng_state(self, state):
        """Set the internal PRNG state, e.g. after unpickling"""
        self.prng.setstate(state)

    def reseed_prng(self, seed):
        """Reseed the internal PRNG"""
        self.prng.seed(seed)

    def get_phase(self):
        """Return the current phase this simulation state is in"""
        return self.phase

    def set_phase(self, phase, *, error_on_repeat=False):
        """Update the state to show that it is in a given phase."""

        if not isinstance(phase, SimulationPhase):
            raise ValueError(("Phase should be set to a SimulationPhase object, not "
                              f"'{type(phase).__name__}'"))

        if error_on_repeat:
            if self.is_phase_complete(phase):
                raise ValueError(f"Phase {phase} has already been run.")

        # Check we're running this phase only after prerequisites are complete
        log.info("Checking simulation has prerequisites for this phase...")
        for i in range(int(phase)):
            if not self.is_phase_complete(SimulationPhase(i)):
                log.warning(("Attempting to run phase %i ('%s') but a previous state ('%s') has"
                             " not completed yet.  This will probably fail and will definitely"
                             " mean that the output is incomparable due to PRNG state changes."),
                            i, phase.name, SimulationPhase(i).name)
                self.dirty = True

        # Check we've not previously run this phase
        if self.is_phase_complete(phase):
            log.warning(("Phase %s has already been run.  Re-running will change the state of the"
                         " PRNG and lead to unreliable output.  The simulation will be marked as"
                         " dirty to record this"), phase.name)
            self.dirty = True

        self.phase = phase
