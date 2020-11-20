"""Components for the simulation"""

import logging
import pickle
from typing import Optional

from abmlux.random_tools import Random
from abmlux.config import Config
from abmlux.telemetry import TelemetryServer

log = logging.getLogger("component")

#pylint: disable=attribute-defined-outside-init
class Component:
    """A pluggable simulation component."""

    def __init__(self, component_config: Config):

        self.config = component_config
        self.telemetry_server: Optional[TelemetryServer] = None

        if "__prng_seed__" in component_config:
            self.prng = Random(float)
        else:
            self.prng   = Random()


    def set_telemetry_server(self, telemetry_server: Optional[TelemetryServer]) -> None:
        self.telemetry_server = telemetry_server

    def report(self, topic, payload):
        if self.telemetry_server is None:
            return

        self.telemetry_server.send(topic, payload)

    def init_sim(self, sim) -> None:
        """Complete initialisation of this object with the full state of a ready-to-go simulation.

        It is expected that this is a chance to hook onto the event bus."""

        self.sim = sim
        self.bus = sim.bus

# # Components have
#  - Their own config
#  - Build phase where they get ready to be passed to a simulation
#  - "start simulation" call where they know things about other components (and the messagebus)
# # during the sim
#  - Enable and disable
#  - Change the value of certain variables (pre-register at start simulation)
#  - "freeze" back into a portable component (to be put into a new simulation)
#  - Expose information to the reporter (observers or publishing state?)
#  - 