"""Reporters that output to CSV files"""

import os
import os.path
import csv
from collections import defaultdict

from abmlux.reporters import Reporter

class HealthStateCounts(Reporter):
    """Reporter that writes to a CSV file as it runs."""

    def __init__(self, host, port, config):
        super().__init__(host, port)

        self.filename               = config['filename']

        self.subscribe("simulation.start", self.start_sim)
        self.subscribe("simulation.end", self.stop_sim)
        self.subscribe("world.updates", self.tick_updates)

    def start_sim(self, run_id, created_at, clock, world, disease_states):
        """Called when the simulation starts.  Writes headers and creates the file handle."""

        # TODO: handle >1 sim at the same time using the run_id

        self.counts = defaultdict(int)
        self.states = disease_states
        for agent in world.agents:
            self.counts[agent.health] += 1

        # Check dir exists and open handle
        dirname = os.path.dirname(self.filename)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        # Write header
        header = ["time", "date"]
        header += self.states

        self.writer.writerow(header)

    def tick_updates(self, clock, update_notifications):
        """Update the CSV, writing a single row for every clock tick"""
        #if self.writer is None or self.handle is None:
        #    raise AttributeError("Call to iterate before call to start()")

        health_updates = [n for n in update_notifications if n[0] == 'notify.agent.health']
        for _, agent, old_health in health_updates:
            self.counts[old_health] -= 1
            self.counts[agent.health] += 1

        row =  [clock.t, clock.iso8601()]
        row += [self.counts[k] for k in self.states]
        self.writer.writerow(row)

    def stop_sim(self):
        """Called when the simulation ends.  Closes the file handle."""
        if self.handle is not None:
            self.handle.close()
