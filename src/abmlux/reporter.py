"""Represents a class used to report data from the simulation."""

import logging

log = logging.getLogger("reporter")

class Reporter:
    """Reports on the status of the abm simulation.

    Used to record data to disk, report to screen, compute summary statistics,
    or stream to other logging tools over the network."""

    def start(self, sim):
        """Called when the simulation starts"""
        pass

    def iterate(self, sim):
        """Called on every iteration of the simulation"""
        pass

    def stop(self, sim):
        """Called when the simulation stops"""
        pass
