"""Models in this package represent the actions of agents within the system."""

from abmlux.component import Component

class ActivityModel(Component):
    """Represent activity transitions for agents in the simulation.

    This usually happens by emitting request.agent.activity events in response to clock updates
    from the simulation."""

    def __init__(self, config, activity_manager):

        super().__init__(config)

        self.activity_manager = activity_manager
