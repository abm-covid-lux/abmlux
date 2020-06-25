
from datetime import timedelta

class SimClock:
    """Tracks time ticking forward one 'tick' at a time."""

    def __init__(self, tick_length_s, simulation_length_days=100):

        self.tick_length_s = tick_length_s
        self.ticks_in_minute = 60       / self.tick_length_s
        self.ticks_in_hour   = 3600     / self.tick_length_s
        self.ticks_in_day    = 86400    / self.tick_length_s
        self.ticks_in_week   = 604800   / self.tick_length_s

        self.t             = 0
        self.max_ticks     = int(self.days_to_ticks(simulation_length_days))


    def __iter__(self):
        return self

    def __next__(self):
        self.t += 1
        if self.t > self.max_ticks:
            raise StopIteration()
        return self.t

    def __len__(self):
        return self.max_ticks

    def ticks_elapsed(self):
        return self.t

    def ticks_remaining(self):
        return self.max_ticks - self.t

    def time_elapsed(self):
        return self.ticks_to_timedelta(self.t)

    def time_remaining(self):
        return self.ticks_to_timedelta(self.max_ticks) - self.time_elapsed()

    def seconds_elapsed(self):
        return self.t * self.tick_length_s

    def minutes_elapsed(self):
        return self.t / self.ticks_in_minute

    def hours_elapsed(self):
        return self.t / self.ticks_in_hour

    def days_elapsed(self):
        return self.t / self.ticks_in_day

    def weeks_elapsed(self):
        return self.t / self.ticks_in_week

    def days_to_ticks(self, days):
        return days * self.ticks_in_day

    def timedelta_to_ticks(self, td):
        return td.total_seconds() / self.tick_length_s

    def ticks_to_timedelta(self, ticks):
        return timedelta(seconds=ticks * self.tick_length_s)

