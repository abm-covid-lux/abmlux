"""Components for the simulation"""

import logging
import pickle

from abmlux.config import Config

log = logging.getLogger("component")

class Component:
    """A pluggable simulation component."""


    def __init__(self, component_config: Union[Config, dict]):

        self.config = component_config

    def to_file(self, output_filename: str) -> None:
        """Write an object to disk at the filename given.

        Parameters:
            output_filename (str):The filename to write to.  Files get overwritten
                                by default.

        Returns:
            None
        """

        log.info("Writing to %s...", output_filename)
        with open(output_filename, 'wb') as fout:
            pickle.dump(self, fout, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def from_file(input_filename: str) -> Component:
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


    #def register_var(self, name, default_value):
    #    self.name = default_value
    #    self.variables[name] = self.name





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