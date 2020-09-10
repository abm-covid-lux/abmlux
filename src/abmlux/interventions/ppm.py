"""Represents the intervention of personal protective measures such as face masks."""

import math
import logging
from tqdm import tqdm
from collections import deque, defaultdict

from abmlux.sim_time import DeferredEventPool
import abmlux.random_tools as random_tools
from abmlux.interventions import Intervention


class PersonalProtectiveMeasures(Intervention):

    def __init__(self, prng, config, clock, bus, state):
        super().__init__(prng, config, clock, bus)

        pass
