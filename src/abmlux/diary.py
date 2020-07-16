"""Represents time-of-use data within the system, as lists of activities
in-order.

There are two types of object: daily routines, which represent a day's activities,
and weekly routines, which have weekend and weekday routines stitched together
to form a single list of activities."""

import uuid
from enum import IntEnum

class DayOfWeek(IntEnum):
    """Indexes the day of the week as read from time of use data"""

    SUNDAY    = 0
    MONDAY    = 1
    TUESDAY   = 2
    WEDNESDAY = 3
    THURSDAY  = 4
    FRIDAY    = 5
    SATURDAY  = 6


class DiaryDay:
    """A single day out of the time of use study."""
    # pylint: disable=too-few-public-methods

    def __init__(self, identity, age, day, weight, daily_routine):
        """Represents a daily routine as read from time-of-use survey data.

        Routine is assumed to start at midnight.

        Parameters:
          identity (string):The original identity of the person from the survey
          age (int):The participant age
          day (DayOfWeek):The day of week this represents
          weight (float):Statistical weight given to this routine
          daily_routine (list):List of activities performed during this routine.
                               Length of list should be however many ticks there
                               are in a simulation day.
        """
        # Container class for data we don't control, so pylint can be quiet
        # pylint: disable=too-many-arguments

        self.uuid          = uuid.uuid4().hex
        self.identity      = identity
        self.age           = age
        self.day           = DayOfWeek(day)     # DayOfWeek
        self.weight        = weight
        self.daily_routine = daily_routine

    def __str__(self):
        return (f"<DiaryDay {self.uuid}; identity={self.identity}, "
                f"day={self.day}, age={self.age}, "
                f"weight={self.weight}>")


class DiaryWeek:
    """A week's routine out of the time of use study"""
    # pylint: disable=too-few-public-methods

    def __init__(self, identity, age, weight, weekly_routine):
        """Represents a weekly routine as read from time-of-use survey data.

        Routine is assumed to start at the start of the week, i.e. Sunday at 00:00

        Parameters:
          identity (string):The original identity of the person from the survey
          age (int):The participant age
          weight (float):Statistical weight given to this routine
          weekly_routine (list):List of activities performed during this routine.
                                Length of list should be however many ticks there
                                are in a simulation week.
        """
        self.uuid           = uuid.uuid4().hex
        self.identity       = identity
        self.age            = age
        self.weight         = weight
        self.weekly_routine = weekly_routine

    def __str__(self):
        return (f"<DiaryWeek {self.uuid}; identity={self.identity}, "
                f"age={self.age}, weight={self.weight}>")
