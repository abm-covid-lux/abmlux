"""Components for the simulation"""

import logging
import pickle
from typing import Optional, Callable

from abmlux.random_tools import Random
from abmlux.config import Config
from abmlux.messagebus import MessageBus

log = logging.getLogger("component")

#pylint: disable=attribute-defined-outside-init
class Component:
    """A pluggable simulation component."""

    def __init__(self, component_config: Config):

        self.config = component_config
        self.telemetry_bus: Optional[MessageBus] = None
        self.registered_variables: set[str] = set()

        if "__prng_seed__" in component_config:
            self.prng = Random(self.config['__prng_seed__'])
        else:
            self.prng   = Random()

    def register_variable(self, variable_name):
        """Register a variable as editable at runtime."""
        self.registered_variables.add(variable_name)

    def set_registered_variable(self, variable_name, new_value):
        """Set the value of a registered variable.

        If the set_variable_name function exists then this will be called with the value to set.
        If the variable exists in this object, its value will simply be set.
        """

        if variable_name not in self.registered_variables:
            raise AttributeError(f"Attempt to set variable {variable_name} but it is not "
                                 f"in the list of variables for this object ({self})")

        if hasattr(self, f"set_{variable_name}"):
            getattr(self, f"set_{variable_name}")(new_value)
        elif hasattr(self, variable_name):
            setattr(self, variable_name, new_value)
        else:
            raise AttributeError(f"Attempt to set variable {variable_name} but it does not exist.")

    def set_telemetry_bus(self, telemetry_bus: Optional[MessageBus]) -> None:
        self.telemetry_bus = telemetry_bus

    def report(self, topic, *args, **kwargs):
        """Publish a message to the telemetry bus, informing reporters of some interesting event
        or statistic."""

        if self.telemetry_bus is None:
            return

        self.telemetry_bus.publish(topic, *args, **kwargs)

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
