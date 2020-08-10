"""Reporters that output to CSV files"""

import csv

from abmlux.reporter import Reporter

class HealthStateCounts(Reporter):
    """Reporter that writes to a CSV file as it runs."""

    def __init__(self, filename):
        self.filename = filename
        self.handle   = None
        self.writer   = None

    def start(self, sim):
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        # Write header
        header = []
        header.append("time")
        header += [k for k, v in sim.agents_by_health_state.items()]

        self.writer.writerow(header)

    def iterate(self, sim):
        if self.writer is None or self.handle is None:
            raise AttributeError("Call to iterate before call to start()")

        row = []
        row.append(sim.clock.t)
        row += [len(v) for k, v in sim.agents_by_health_state.items()]

        self.writer.writerow(row)

    def stop(self, sim):
        if self.handle is not None:
            self.handle.close()
