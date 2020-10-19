"""Models in this package represent the actions of agents within the system."""

class ActivityModel:
    """Represent activity transitions for agents in the simulation.

    This usually happens by emitting request.agent.activity events in response to clock updates
    from the simulation."""

    def __init__(self, prng, config, bus, activity_manager):

        self.prng             = prng
        self.config           = config
        self.bus              = bus
        self.activity_manager = activity_manager
