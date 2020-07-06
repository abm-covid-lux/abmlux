

import uuid
from enum import IntEnum

class DayOfWeek(IntEnum):

    SUNDAY    = 1
    MONDAY    = 2
    TUESDAY   = 3
    WEDNESDAY = 4
    THURSDAY  = 5
    FRIDAY    = 6
    SATURDAY  = 7


class DiaryDay:
    """A single day out of the time of use study."""


    def __init__(self, identity, age, day, weight, daily_routine):
        self.uuid          = uuid.uuid4().hex
        self.identity      = identity
        self.age           = age
        self.day           = DayOfWeek(day)     # DayOfWeek
        self.weight        = weight
        self.daily_routine = daily_routine

    def inspect(self):
        return (f"<DiaryDay {self.uuid}; identity={self.identity}, "
                f"day={self.day}, age={self.age}, "
                f"weight={self.weight}>")



class DiaryWeek:
    """A week's routine out of the time of use study"""


    def __init__(self, identity, age, weight, weekly_routine):
        self.uuid           = uuid.uuid4().hex
        self.identity       = identity
        self.age            = age
        self.weight         = weight
        self.weekly_routine = weekly_routine

    def inspect(self):
        return (f"<DiaryWeek {self.uuid}; identity={self.identity}, "
                f"age={self.age}, weight={self.weight}>")

