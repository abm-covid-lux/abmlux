"""Represents interventions to the system."""

import math
import logging
from tqdm import tqdm
from collections import deque, defaultdict

from abmlux.sim_time import DeferredEventPool
import abmlux.random_tools as random_tools

log = logging.getLogger("location_closure")

class LocationClosures(Intervention):

    def __init__(self, prng, config, clock, bus, state):
        super().__init__(prng, config, clock, bus)

        pass