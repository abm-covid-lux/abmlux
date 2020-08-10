"""Base class for all disease models"""

import logging

log = logging.getLogger("disease_model")

class DiseaseModel:
    """Represents a disease type within the system"""

    def __init__(self, states):

        self.states = states

    def initialise_agents(self, network):
        """Create initial health states for agents on a network.

        Operates on Agent list in place (does not return a value)"""

        log.warning("STUB: initialise_agents in disease.py")

    def get_health_transitions(self, t, sim):
        """Return a list of health transitions agents should enact this tick.

        This is in the form of a list of tuples (agent, health_state)"""

        log.warning("STUB: get_health_transitions in disease.py")
        return []
