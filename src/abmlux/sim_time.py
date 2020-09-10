"""Synchronous, monotonic clock reporting sim 'ticks'.

Used to represent time in the model."""

import logging
from collections import defaultdict
from datetime import datetime,timedelta

import dateparser

log = logging.getLogger("sim_time")

class SimClock:
    """Tracks time ticking forward one 'tick' at a time."""
    # They're appropriate in this case.
    # pylint: disable=too-many-instance-attributes

    def __init__(self, tick_length_s, simulation_length_days=100, epoch=datetime.now()):
        """Create a new clock.

        This clock counts forward in time by a set amount every tick, ignoring timezone
        changes and other complexities.

        The simulation deals with a weekly repeating cycle, and as such the time ticks used
        must repeat regularly throughout the week.  This means time ticks must be a length
        that is divisible by the length of a week.

        Parameters:
            tick_length_s (int):Number of wall-clock seconds per simulation tick
            simulation_length_days (int):How many days will this simulation run for?
            epoch (str or datetime):A datetime representing the starting point for the sim.
        """

        # Check we have the same number of ticks in every week.
        # This is necessary to enforce weekly routines in the system, and should
        # be changed if we ever move away from a weekly routine
        if 604800 % tick_length_s != 0:
            raise ValueError("Tick length must be divisible by week length")

        if isinstance(epoch, str):
            epoch = dateparser.parse(epoch)

        self.tick_length_s = tick_length_s
        self.ticks_in_second = 1          / self.tick_length_s
        self.ticks_in_minute = 60         / self.tick_length_s
        self.ticks_in_hour   = 3600       / self.tick_length_s
        self.ticks_in_day    = 86400      / self.tick_length_s
        self.ticks_in_week   = int(604800 / self.tick_length_s)

        self.epoch             = epoch
        self.epoch_week_offset = int(self.epoch.weekday() * self.ticks_in_day \
                                 + self.epoch.hour        * self.ticks_in_hour \
                                 + self.epoch.minute      * self.ticks_in_minute \
                                 + self.epoch.second      * self.ticks_in_second)
        self.max_ticks         = int(self.days_to_ticks(simulation_length_days))

        self.t       = 0
        self.started = False
        self.reset()

        log.info("New clock created at %s, tick_length=%i, simulation_days=%i, week_offset=%i",
                 self.epoch, tick_length_s, simulation_length_days, self.epoch_week_offset)

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
        # TODO: speed this up by doing dead reckonining
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
        """Return the number of ticks remaining before the end of the simulation"""
        return self.max_ticks - self.t

    def time_elapsed(self):
        """Return the time elapsed, as a timedelta object"""
        return self.ticks_to_timedelta(self.t)

    def time_remaining(self):
        """Return the time remaining, as a timedelta object"""
        return self.ticks_to_timedelta(self.max_ticks - self.t)

    def seconds_elapsed(self):
        """Return the number of seconds elapsed since the start of the simulation"""
        return self.t * self.tick_length_s

    def minutes_elapsed(self):
        """Return the number of minutes elapsed since the start of the simulation"""
        return self.t / self.ticks_in_minute

    def hours_elapsed(self):
        """Return the number of hours elapsed since the start of the simulation"""
        return self.t / self.ticks_in_hour

    def days_elapsed(self):
        """Return the number of days elapsed since the start of the simulation"""
        return self.t / self.ticks_in_day

    def weeks_elapsed(self):
        """Return the number of weeks elapsed since the start of the simulation"""
        return self.t / self.ticks_in_week

    def mins_to_ticks(self, mins):
        """Convert a number of minutes to a number of simulation ticks"""
        return mins * self.ticks_in_minute

    def days_to_ticks(self, days):
        """Convert a number of days to a number of simulation ticks"""
        return days * self.ticks_in_day

    def timedelta_to_ticks(self, timed):
        """Convert a timedelta object to a number of simulation ticks"""
        return timed.total_seconds() / self.tick_length_s

    def ticks_to_timedelta(self, ticks):
        """Convert a number of simulation ticks to a timedelta object"""
        return timedelta(seconds=ticks * self.tick_length_s)



class DeferredEventPool:

    def __init__(self, bus, clock):
        self.events = defaultdict(list)
        self.bus = bus
        self.clock = clock

        self.bus.subscribe("sim.time.tick", self.tick)

    def add(self, topic, lifespan, *args, **kwargs):

        if lifespan is None and deadline is None:
            raise ValueError("Timer must have a deadline or a lifespan set")

        self.deadline = self.clock.t + self._duration_to_ticks(lifespan)
        self.events[self.deadline].append((topic, args, kwargs))

    def tick(self, clock, t):
        for event in self.events[t]:
            topic, args, kwargs = event
            self.bus.publish(topic, *args, **kwargs)

        del(self.events[t])

    def _duration_to_ticks(self, time_ref):
        """Converts a duration in raw ticks or timedelta into a number of ticks
        in the current clock"""

        # Already a tick count
        if isinstance(time_ref, int):
            return time_ref

        # A duration object
        if isinstance(time_ref, timedelta):
            return int(self.clock.timedelta_to_ticks(time_ref))

        raise ValueError(f"Timer parameter given as a {type(time_ref)}, but expecting int or "\
                          "timedelta")