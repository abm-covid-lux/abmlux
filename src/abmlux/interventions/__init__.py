"""Module containing intervention classes.

Interventions modify the simulation by emitting and responding to events that happen.  Some
of these events are absorbed by the simulation and change the status of the net.  Others are
listened to by other, stateful, interventions (such as quarantine), effectively extending
the state of the simulation."""

import logging

from abmlux.component import Component

log = logging.getLogger("intervention")


class Intervention(Component):
    """Represents an intervention within the system.

    Interventions are notified of simulation state on every tick, allowing them to
    build internal state and return a list of activity changes in order to affect the simulation"""

    def __init__(self, config, init_enabled: bool):

        super().__init__(config)

        # Updated to say whether the intervention is enabled or not at the current time
        self.enabled = init_enabled

    def enable(self):
        """Called when the intervention should be enabled.

        This may simply set internal state
        Interventions may need some time to disable/enable, which is allowed."""

        self.enabled = True

    def disable(self):
        """Called when the intervention should be disabled.

        This may simply set internal state, or cause the intervention to clean up.
        Interventions may need some time to disable/enable, which is allowed."""

        self.enabled = False
