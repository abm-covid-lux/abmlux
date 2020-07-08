"""Represents a class used to report data from the simulation."""

from datetime import datetime
import logging
import csv

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

    def finalise(self, sim):
        """Called when the simulation stops"""
        pass


class BasicCLIReporter(Reporter):
    """Reports simple stats on the running simulation to the terminal."""

    def __init__(self):
        self.start_time = None
        self.stop_time = None

    def start(self, sim):
        self.start_time = datetime.now()
        print(f"Starting simulation at {self.start_time}")

    def iterate(self, sim):
        print(f"[{(100 * sim.clock.t / sim.clock.max_ticks):.2f}%: {sim.clock.now()}] { {k.name[0]: len(v) for k, v in sim.agents_by_health_state.items()} }")

    def finalise(self, sim):
        self.stop_time = datetime.now()
        print(f"Ending simulation at {self.stop_time} ({self.stop_time - self.start_time})")


class CSVReporter(Reporter):
    """Reporter that writes to a CSV file as it runs."""

    def __init__(self, filename):
        self.filename = filename
        self.handle = None
        self.writer = None

    def start(self, sim):
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        header = []
        header.append("time")
        header += [k.name for k, v in sim.agents_by_health_state.items()]

        self.writer.writerow(header)

    def iterate(self, sim):
        if self.writer is None or self.handle is None:
            raise AttributeError("Call to iterate before call to start()")

        row = []
        row.append(sim.clock.t)
        row += [len(v) for k, v in sim.agents_by_health_state.items()]

        self.writer.writerow(row)

    def finalise(self, sim):
        if self.handle is not None:
            self.handle.close()
