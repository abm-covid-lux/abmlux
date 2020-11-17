"""Represents the simulation state.  Is built gradually by the various model stages, ands then
ingested by the simulator as it runs."""

import logging
import uuid
from datetime import datetime
from typing import Union

from abmlux.activity_manager import ActivityManager
from abmlux.location_manager import LocationManager
from abmlux.config import Config
from abmlux.sim_time import SimClock
from abmlux.version import VERSION
from abmlux.map import Map
from abmlux.simulator import Simulator
from abmlux.disease_model import DiseaseModel
from abmlux.activity import ActivityModel
from abmlux.movement_model import MovementModel
from abmlux.network import Network
from abmlux.interventions import Intervention

log = logging.getLogger("sim_state")



class SimulationFactory:
    """Class that allows for gradual composition of a number of components, eventually outputting
    a simulator object that can be used to run simulations with the config given."""

    def __init__(self, config: Config):

        # Static info
        self.abmlux_version = VERSION
        self.created_at     = datetime.now()
        self.run_id         = uuid.uuid4().hex

        log.info("Simulation state created at %s with ID=%s", self.created_at, self.run_id)

        self.config                 = config
        self.activity_manager       = ActivityManager(config['activities'])
        self.location_manager       = LocationManager(config['locations'])
        self.clock                  = SimClock(config['tick_length_s'],
                                               config['simulation_length_days'], config['epoch'])

        # Components of the simulation
        self.map                    = None
        self.network                = None
        self.activity_model         = None
        self.movement_model         = None
        self.disease_model          = None
        self.interventions          = {}
        self.intervention_schedules = {}

    # FIXME: move 'add' to be 'set' for the singular items below
    def set_movement_model(self, movement_model: MovementModel) -> None:
        self.movement_model = movement_model

    def set_disease_model(self, disease_model: DiseaseModel) -> None:
        self.disease_model = disease_model

    def set_activity_model(self, activity_model: ActivityModel) -> None:
        self.activity_model = activity_model

    def set_network_model(self, network: Network) -> None:
        self.network = network

    def set_map(self, _map: Map) -> None:
        self.map = _map

    def add_intervention(self, name: str, intervention: Intervention) -> None:
        self.interventions[name] = intervention

    def add_intervention_schedule(self, intervention: Intervention,
                                  schedule: dict[Union[str, int], str]) -> None:
        self.intervention_schedules[intervention] = schedule

    def new_sim(self):
        """Return a new simulator based on the config above."""
        # FIXME: this should be runnable multiple times without any impact on the data integrity.

        if self.map is None:
            raise ValueError("No Map")
        if self.network is None:
            raise ValueError("No network defined.")
        if self.activity_model is None:
            raise ValueError("No activity model defined.")
        if self.movement_model is None:
            raise ValueError("No location model defined.")
        if self.disease_model is None:     # FIXME: rename disease_model
            raise ValueError("No disease model defined.")
        if self.interventions is None:
            raise ValueError("No interventions defined.")
        if self.intervention_schedules is None:
            raise ValueError("No interventions scheduler defined.")

        sim = Simulator(self.config, self.activity_manager, self.clock, self.map,
                        self.network, self.activity_model, self.movement_model,
                        self.disease_model, self.interventions, self.intervention_schedules)

        return sim
