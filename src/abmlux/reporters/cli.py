"""Reporters that output to the terminal"""


from datetime import datetime

from tqdm import tqdm

from abmlux.reporter import Reporter


class TQDM(Reporter):
    """Uses TQDM to plot a progress bar"""

    def __init__(self):
        self.pbar = None

    def start(self, sim):
        self.pbar = tqdm(total=sim.clock.max_ticks)

    def iterate(self, sim):
        self.pbar.update()
        desc = ", ".join([f"{k.name[0]}:{len(v)}" for k, v in sim.agents_by_health_state.items()])
        self.pbar.set_description(f"{desc} {sim.clock.now()}")

    def stop(self, sim):
        self.pbar.close()

class BasicProgress(Reporter):
    """Reports simple stats on the running simulation to the terminal."""

    def __init__(self):
        self.start_time = None
        self.stop_time = None

    def start(self, sim):
        self.start_time = datetime.now()
        print(f"Starting simulation at {self.start_time}")

    def iterate(self, sim):
        print(f"[t={sim.clock.t}, {(100 * sim.clock.t / sim.clock.max_ticks):.2f}%: "
              f"{sim.clock.now()}] { {k.name[0]: len(v) for k, v in sim.agents_by_health_state.items()} }")

    def stop(self, sim):
        self.stop_time = datetime.now()
        print(f"Ending simulation at {self.stop_time} ({self.stop_time - self.start_time})")
