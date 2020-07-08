"""Represents a class used to report data from the simulation."""


from datetime import datetime

class Reporter:
    """Reports on the status of the abm simulation.

    Used to record data to disk, report to screen, compute summary statistics,
    or stream to other logging tools over the network."""


    def __init__(self):
        pass

    def start(self):
        """Called when the simulation starts"""
        pass

    def iterate(self):
        """Called on every iteration of the simulation"""
        pass

    def finalise(self):
        """Called when the simulation stops"""
        pass


class BasicCLIReporter(Reporter):
    """Reports simple stats on the running simulation to the terminal."""

    def __init__(self):

        self.start_time = None
        self.stop_time = None

    def start(self):
        self.start_time = datetime.now()
        print(f"Starting simulation at {self.start_time}")

    def iterate(self):
        # print(f"[{t}: {clock.now()}] { {k.name[0]: len(v) for k, v in agents_by_health_state.items()} }, {len(health_changes)} dhealth, {len(activity_changes)} dactivity")
        pass

    def finalise(self):
        self.stop_time = datetime.now()
        print(f"Ending simulation at {self.stop_time} ({self.stop_time - self.start_time})")
