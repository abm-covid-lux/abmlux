"""Represents a class used to report data from the simulation."""


from datetime import datetime

class Reporter:
    """Reports on the status of the abm simulation.

    Used to record data to disk, report to screen, compute summary statistics,
    or stream to other logging tools over the network."""

    def __init__(self):
        pass

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
        print(f"[{sim.clock.t}: {sim.clock.now()}] { {k.name[0]: len(v) for k, v in sim.agents_by_health_state.items()} }")

    def finalise(self, sim):
        self.stop_time = datetime.now()
        print(f"Ending simulation at {self.stop_time} ({self.stop_time - self.start_time})")
