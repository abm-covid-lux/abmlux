"""Reporters that output to the terminal"""


from datetime import datetime

from tqdm import tqdm

from abmlux.reporters import Reporter


class TQDM(Reporter):
    """Uses TQDM to plot a progress bar"""

    def __init__(self, bus):

        self.pbar    = None
        self.sim     = None
        self.disease = None

        bus.subscribe("notify.time.start_simulation", self.start, self)
        bus.subscribe("notify.time.tick", self.iterate, self)
        bus.subscribe("notify.time.end_simulation", self.stop, self)

    def start(self, sim):
        self.sim     = sim
        self.disease = sim.disease
        self.pbar    = tqdm(total=sim.clock.max_ticks)

    def iterate(self, clock, t):
        self.pbar.update()
        # TODO: The below summarises the states using a simple str() call.
        #       This is okay, but the disease model provides tools to get a single-letter
        #       representation of the health state, and that should be used instead.
        # FIXME: the below uses what _should_ really be a private variable, it should be replaced
        #        by a state-change counter listening to events within this class
        desc = ", ".join([f"{str(k)[0]}:{len(v)}" \
                          for k, v in self.disease.agents_by_health_state.items()])
        self.pbar.set_description(f"{desc} {clock.now()}")

    def stop(self, sim):
        self.pbar.close()
