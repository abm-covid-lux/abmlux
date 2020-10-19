"""Module containing intervention classes.

Interventions modify the simulation by emitting and responding to events that happen.  Some
of these events are absorbed by the simulation and change the status of the net.  Others are
listened to by other, stateful, interventions (such as quarantine), effectively extending
the state of the simulation."""

import logging

log = logging.getLogger("intervention")


class Intervention:
    """Represents an intervention within the system.

    Interventions are notified of simulation state on every tick, allowing them to
    build internal state and return a list of activity changes in order to affect the simulation"""

    def __init__(self, prng, config, clock, bus):

        self.prng   = prng
        self.config = config
        self.clock  = clock
        self.bus    = bus

    def initialise_agents(self, network):
        """Initialise internal state for this intervention, potentially
        modifying the network if necessary.  Run prior to simulation start."""
