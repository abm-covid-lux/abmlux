"""Synchronous, monotonic clock reporting sim 'ticks'.

Used to represent time in the model."""

import logging
from collections import defaultdict
from datetime import datetime,timedelta
from typing import Union

import dateparser

from abmlux.messagebus import MessageBus

log = logging.getLogger("sim_time")

class SimClock:
    """Tracks time ticking forward one 'tick' at a time."""
    # They're appropriate in this case.
    # pylint: disable=too-many-instance-attributes

    def __init__(self, tick_length_s: int, simulation_length_days: int=100,
                 epoch: Union[datetime, str]=datetime.now()):
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
            parsed_epoch = dateparser.parse(epoch)
            if parsed_epoch is None:
                raise ValueError(f"Failed to parse epoch: {epoch}")
            self.epoch = parsed_epoch
        else:
            self.epoch = epoch

        self.tick_length_s = tick_length_s
        self.ticks_in_second = 1          / self.tick_length_s
        self.ticks_in_minute = 60         / self.tick_length_s
        self.ticks_in_hour   = 3600       / self.tick_length_s
        self.ticks_in_day    = 86400      / self.tick_length_s
        self.ticks_in_week   = int(604800 / self.tick_length_s)

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

    def reset(self) -> None:
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

    def tick(self) -> int:
        """Iterate the clock by a single tick"""
        return next(self)

    def now(self) -> datetime:
        """Return a datetime.datetime showing the clock time"""
        # TODO: speed this up by doing dead reckonining
        #        instead of using the date libs
        return self.epoch + self.time_elapsed()

    def ticks_through_week(self) -> int:
        """Returns the number of whole ticks through the week this is"""
        return int((self.epoch_week_offset + self.t) % self.ticks_in_week)

    def ticks_elapsed(self) -> int:
        """Return the number of ticks elapsed since the start of the simulation.

        Equivalent to self.t"""
        return self.t

    def ticks_remaining(self) -> int:
        """Return the number of ticks remaining before the end of the simulation"""
        return self.max_ticks - self.t

    def time_elapsed(self) -> timedelta:
        """Return the time elapsed, as a timedelta object"""
        return self.ticks_to_timedelta(self.t)

    def time_remaining(self) -> timedelta:
        """Return the time remaining, as a timedelta object"""
        return self.ticks_to_timedelta(self.max_ticks - self.t)

    def seconds_elapsed(self) -> float:
        """Return the number of seconds elapsed since the start of the simulation"""
        return self.t * self.tick_length_s

    def minutes_elapsed(self) -> float:
        """Return the number of minutes elapsed since the start of the simulation"""
        return self.t / self.ticks_in_minute

    def hours_elapsed(self) -> float:
        """Return the number of hours elapsed since the start of the simulation"""
        return self.t / self.ticks_in_hour

    def days_elapsed(self) -> float:
        """Return the number of days elapsed since the start of the simulation"""
        return self.t / self.ticks_in_day

    def weeks_elapsed(self) -> float:
        """Return the number of weeks elapsed since the start of the simulation"""
        return self.t / self.ticks_in_week

    def mins_to_ticks(self, mins: float) -> float:
        """Convert a number of minutes to a number of simulation ticks"""
        return mins * self.ticks_in_minute

    def days_to_ticks(self, days: float) -> float:
        """Convert a number of days to a number of simulation ticks"""
        return days * self.ticks_in_day

    def timedelta_to_ticks(self, timed: timedelta) -> float:
        """Convert a timedelta object to a number of simulation ticks"""
        return timed.total_seconds() / self.tick_length_s

    def ticks_to_timedelta(self, ticks: float) -> timedelta:
        """Convert a number of simulation ticks to a timedelta object"""
        return timedelta(seconds=ticks * self.tick_length_s)

    def datetime_to_ticks(self, time: Union[str, datetime]) -> float:
        # TODO: write tests for this method
        """Convert an actual datetime to ticks, based on the epoch of the clock.

        time May be a datetime object or a string representing a datetime, parsed using
        dateutils.parser
        """
        if isinstance(time, str):
            parsed_time = dateparser.parse(time)
            if parsed_time is None:
                raise ValueError(f"Unable to parse time: {time}")
            time = parsed_time

        return self.timedelta_to_ticks(time - self.epoch)

Duration = Union[int, timedelta]

class DeferredEventPool:
    """Fires events at a future time, publishing onto the event bus given"""

    def __init__(self, bus: MessageBus, clock: SimClock):
        self.events: defaultdict[int, list]     = defaultdict(list)
        self.bus        = bus
        self.clock      = clock

        self.bus.subscribe("notify.time.tick", self.tick, self)

    def add(self, topic: int, lifespan: Duration, *args, **kwargs):
        """Add an event to the pool, to be fired later with the arguments given.

        Parameters:
            topic: The topic to publish an event on
            lifespan: The delay, i.e. how long to wait before publishing
            *args, **kwargs: passed to the callback.
        """

        if lifespan is None:
            raise ValueError("Timer must have a lifespan set")

        deadline = self.clock.t + self._duration_to_ticks(lifespan)
        self.events[deadline].append((topic, args, kwargs))

    # pylint: disable=unused-argument
    def tick(self, clock: SimClock, t: int) -> None:
        """Called as a callback when the timer ticks.

        This is used to decide which deferred events to launch, and should generally not need
        to be called by the user if the messagebus is handling time events."""

        for event in self.events[t]:
            topic, args, kwargs = event
            if isinstance(topic, str):
                self.bus.publish(topic, *args, **kwargs)
            else:
                topic(*args, **kwargs)

        del self.events[t]

    def _duration_to_ticks(self, time_ref: Duration) -> int:
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
