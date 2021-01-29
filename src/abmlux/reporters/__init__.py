"""Represents a class used to report data from the simulation."""

# Allows classes to return their own type, e.g. from_file below
from __future__ import annotations

import logging
from typing import Callable

log = logging.getLogger("reporter")

class Reporter:
    """Reports on the status of the abm simulation.

    Used to record data to disk, report to screen, compute summary statistics,
    or stream to other logging tools over the world."""

    def __init__(self, telemetry_bus):
        super().__init__()

        self.telemetry_bus = telemetry_bus

    def subscribe(self, topic, callback: Callable):
        """Subscribe to a given topic with a set callback"""

        self.telemetry_bus.subscribe(topic, callback, self)
