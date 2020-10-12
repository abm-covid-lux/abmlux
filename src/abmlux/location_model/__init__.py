"""Manages location choice within the model, that is, where agents perform the activities
they are assigned."""

class LocationModel:
    """Defines the location finding behaviour of agents.

    Subclasses are expected to select a location for agents during the simulation, responding to
    activity events and selecting an appropriate location for the agent to perform that activity.
    """

    def __init__(self, prng, config, bus, activity_manager):

        self.prng             = prng
        self.config           = config
        self.bus              = bus
        self.activity_manager = activity_manager
