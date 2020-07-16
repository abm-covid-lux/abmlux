
from datetime import datetime,timedelta
import dateparser

import logging
log = logging.getLogger("sim_time")

class SimClock:
    """Tracks time ticking forward one 'tick' at a time."""

    def __init__(self, tick_length_s, simulation_length_days=100, epoch=datetime.now()):

        # Check we have the same number of ticks in every week.
        #
        # This is necessary to enforce weekly routines in the system, and should
        # be changed if we ever move away from a weekly routine
        if 604800 % tick_length_s != 0:
            raise ValueError("Tick length must be divisible by week length")

        if isinstance(epoch, str):
            epoch = dateparser.parse(epoch)

        self.tick_length_s = tick_length_s
        self.ticks_in_second = 1            / self.tick_length_s
        self.ticks_in_minute = 60           / self.tick_length_s
        self.ticks_in_hour   = 3600         / self.tick_length_s
        self.ticks_in_day    = 86400        / self.tick_length_s
        self.ticks_in_week   = int(604800   / self.tick_length_s)

        self.epoch             = epoch
        self.epoch_week_offset = int(self.epoch.weekday()   * self.ticks_in_day \
                                 + self.epoch.hour          * self.ticks_in_hour \
                                 + self.epoch.minute        * self.ticks_in_minute \
                                 + self.epoch.second        * self.ticks_in_second)
        self.max_ticks         = int(self.days_to_ticks(simulation_length_days))

        self.t       = 0
        self.started = False
        self.reset()

        log.info(f"New clock created at {epoch}, {tick_length_s=}, {simulation_length_days=}, {self.epoch_week_offset=}")

    def reset(self):
        """Reset the clock to the start once more"""
        log.debug("Resetting clock at t=%i", self.t)
        self.t       = 0
        self.started = False

    def __iter__(self):
        self.reset()
        return self

    def __next__(self):

        if self.started:
            self.t += 1
        else:
            self.started = True

        if self.t >= self.max_ticks:
            raise StopIteration()

        return self.t

    def __len__(self):
        return self.max_ticks

    def tick(self):
        """Iterate the clock by a single tick"""
        return next(self)

    def now(self):
        """Return a datetime.datetime showing the clock time"""
        # FIXME: speed this up by doing dead reckonining
        #        instead of using the date libs
        return self.epoch + self.time_elapsed()

    def ticks_through_week(self):
        """Returns the number of ticks through the week this is"""
        return int((self.epoch_week_offset + self.t) % self.ticks_in_week)

    def ticks_elapsed(self):
        """Return the number of ticks elapsed since the start of the simulation.

        Equivalent to self.t"""
        return self.t

    def ticks_remaining(self):
        return self.max_ticks - self.t

    def time_elapsed(self):
        return self.ticks_to_timedelta(self.t)

    def time_remaining(self):
        return self.ticks_to_timedelta(self.max_ticks - self.t)

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

