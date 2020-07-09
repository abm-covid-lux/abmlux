"""Reporters that output to the terminal"""

from datetime import datetime

from abmlux.reporter import Reporter

class BasicProgress(Reporter):
    """Reports simple stats on the running simulation to the terminal."""

    def __init__(self):
        self.start_time = None
        self.stop_time = None

    def start(self, sim):
        self.start_time = datetime.now()
        print(f"Starting simulation at {self.start_time}")

    def iterate(self, sim):
        print(f"[{(100 * sim.clock.t / sim.clock.max_ticks):.2f}%: "
              f"{sim.clock.now()}] { {k.name[0]: len(v) for k, v in sim.agents_by_health_state.items()} }")

    def stop(self, sim):
        self.stop_time = datetime.now()
        print(f"Ending simulation at {self.stop_time} ({self.stop_time - self.start_time})")
