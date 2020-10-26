"""Reporters that output to CSV files"""

import os
import os.path
import csv

from abmlux.reporters import Reporter

class HealthStateCounts(Reporter):
    """Reporter that writes to a CSV file as it runs."""

    def __init__(self, bus, filename):
        self.filename = filename
        self.handle   = None
        self.writer   = None

        self.sim     = None
        self.disease = None

        bus.subscribe("notify.time.start_simulation", self.start, self)
        bus.subscribe("notify.time.tick", self.iterate, self)
        bus.subscribe("notify.time.end_simulation", self.stop, self)

    def start(self, sim):
        """Called when the simulation starts.  Writes headers and creates the file handle."""

        self.sim     = sim
        self.disease = sim.disease

        # Check dir exists and open handle
        dirname = os.path.dirname(self.filename)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        # Write header
        header = ["time", "date"]
        header += [str(k) for k in self.disease.agents_by_health_state.keys()]

        self.writer.writerow(header)

    def iterate(self, clock, t):
        """Update the CSV, writing a single row for every clock tick"""
        #if self.writer is None or self.handle is None:
        #    raise AttributeError("Call to iterate before call to start()")

        row = [t, clock.now()]
        # FIXME: this uses what _should_ be a private variable in the disease model.
        #        it should be replaced by something that does the counts using events internally.
        row += [len(v) for k, v in self.disease.agents_by_health_state.items()]

        self.writer.writerow(row)

    def stop(self, sim):
        """Called when the simulation ends.  Closes the file handle."""
        if self.handle is not None:
            self.handle.close()
