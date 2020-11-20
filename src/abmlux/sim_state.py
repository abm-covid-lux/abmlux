"""Represents the simulation state.  Is built gradually by the various model stages, ands then
ingested by the simulator as it runs."""

# Allows classes to return their own type, e.g. from_file below
from __future__ import annotations

import logging
import uuid
import pickle
from datetime import datetime
from typing import Union

from abmlux.activity_manager import ActivityManager
from abmlux.location_manager import LocationManager
from abmlux.config import Config
from abmlux.sim_time import SimClock
from abmlux.version import VERSION
from abmlux.world.map import Map
from abmlux.simulator import Simulator
from abmlux.disease_model import DiseaseModel
from abmlux.activity import ActivityModel
from abmlux.movement_model import MovementModel
from abmlux.world import World
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
        self.world                  = None
        self.activity_model         = None
        self.movement_model         = None
        self.disease_model          = None
        self.interventions          = {}
        self.intervention_schedules = {}

    def set_movement_model(self, movement_model: MovementModel) -> None:
        self.movement_model = movement_model

    def set_disease_model(self, disease_model: DiseaseModel) -> None:
        self.disease_model = disease_model

    def set_activity_model(self, activity_model: ActivityModel) -> None:
        self.activity_model = activity_model

    def set_world_model(self, world: World) -> None:
        self.world = world

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
        if self.world is None:
            raise ValueError("No world defined.")
        if self.activity_model is None:
            raise ValueError("No activity model defined.")
        if self.movement_model is None:
            raise ValueError("No location model defined.")
        if self.disease_model is None:
            raise ValueError("No disease model defined.")
        if self.interventions is None:
            raise ValueError("No interventions defined.")
        if self.intervention_schedules is None:
            raise ValueError("No interventions scheduler defined.")

        sim = Simulator(self.config, self.activity_manager, self.clock, self.map,
                        self.world, self.activity_model, self.movement_model,
                        self.disease_model, self.interventions, self.intervention_schedules)

        return sim

    def to_file(self, output_filename: str) -> None:
        """Write an object to disk at the filename given.

        Parameters:
            output_filename (str):The filename to write to.  Files get overwritten
                                  by default.

        Returns:
            None
        """

        log.info("Writing to %s...", output_filename)
        # FIXME: error handling
        with open(output_filename, 'wb') as fout:
            pickle.dump(self, fout, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def from_file(input_filename: str) -> SimulationFactory:
        """Read an object from disk from the filename given.

        Parameters:
            input_filename (str):The filename to read from.

        Returns:
            obj(Object):The python object read from disk
        """

        log.info('Reading data from %s...', input_filename)
        with open(input_filename, 'rb') as fin:
            payload = pickle.load(fin)

        return payload
