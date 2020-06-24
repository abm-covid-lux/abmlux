
from datetime import timedelta

class SimClock:
    """Tracks time ticking forward one 'tick' at a time."""

    def __init__(self, tick_length_s, simulation_length_days=100):

        self.tick_length_s = tick_length_s
        self.max_ticks     = self.days_to_ticks(simulation_length_days)
        self.t             = 0

    def tick(self):
        self.t += 1
        return self.t if self.t < self.max_ticks else None

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
        return self.seconds_elapsed() / 60

    def hours_elapsed(self):
        return self.seconds_elapsed() / 3600

    def days_elapsed(self):
        return self.seconds_elapsed() / 86400

    def weeks_elapsed(self):
        return self.seconds_elapsed() / 604800

    # --

    def ticks_in_minute(self):
        return 60 / self.tick_length_s

    def ticks_in_hour(self):
        return 3600 / self.tick_length_s

    def ticks_in_day(self):
        return 86400 / self.tick_length_s

    def ticks_in_week(self):
        return 604800 / self.tick_length_s

    def days_to_ticks(self, days):
        return days * self.ticks_in_day()

    def timedelta_to_ticks(self, td):
        return td.total_seconds() / self.tick_length_s

    def ticks_to_timedelta(self, ticks):
        return timedelta(seconds=ticks * self.tick_length_s)

