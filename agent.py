
from enum import IntEnum

class AgentType(IntEnum):
    """Represents a type for each agent."""

    CHILD   = 0
    ADULT   = 1
    RETIRED = 2


class Agent:
  """Represents a single agent within the simulation"""

  def __init__(self, agetyp, age, location=None):
    # TODO: documentation of argument meaning

    self.agetyp   = agetyp  # Should be an AgentType
    self.age      = age
    self.location = location
