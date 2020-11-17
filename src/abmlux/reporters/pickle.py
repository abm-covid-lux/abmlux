"""Represents a class used to report data from the simulation."""

import os
import os.path as osp
import pickle
import logging

from abmlux.reporter import Reporter

log = logging.getLogger("pickle_reporter")

class StatePickler(Reporter):
    """Writes state to disk at every tick"""

    def __init__(self, dirname):

        self.dirname = dirname
        os.makedirs(self.dirname, exist_ok=True)

    def iterate(self, sim):

        payload = {sim.world}

        with open(osp.join(self.dirname, f"{sim.clock.t}.pickle"), 'wb') as fout:
            pickle.dump(payload, fout)
