"""Represents the simulation state.  Is built gradually by the various model stages, ands then
ingested by the simulator as it runs."""

import logging
import uuid
from datetime import datetime
from enum import IntEnum

from .version import VERSION

log = logging.getLogger("sim_state")

class SimulationPhase(IntEnum):
    """Represents the current stage of the simulation"""

    SETUP    = 0
    RUNNING  = 1
    FINISHED = 2

class SimulationState:

    def __init__(self, config):
        """Create a new state object.

        This object will get gradually built during the setup phase, then
        used during the simulation, after being 'sealed'"""

        self.abmlux_version     = VERSION
        self.created_at         = datetime.now()
        self.run_id             = uuid.uuid4().hex
        self.phase              = SimulationPhase.SETUP
        log.info("Simulation state created at %s with ID=%s", self.created_at, self.run_id)

        self.config               = config
        self.map                  = None
        self.network              = None
        self.activity_initial     = None
        self.activity_transitions = None

    def get_phase(self):
        """Return the current phase this simulation state is in"""
        return self.phase

    def set_phase(self, phase):
        """Update the state to show that it is in a given phase."""

        if not isinstance(phase, SimulationPhase):
            raise ValueError(f"Phase should be set to a SimulationPhase object, not "\
                             f'{type(phase).__name__}'")

        self.phase = phase