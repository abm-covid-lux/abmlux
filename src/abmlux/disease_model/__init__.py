"""Base class for all disease models.

This class represents a disease as a series of states, which is a sufficiently general model
to support many other forms of disease model.
"""

import logging

from abmlux.component import Component

log = logging.getLogger("disease_model")

class DiseaseModel(Component):
    """Represents a disease type within the system"""

    def __init__(self, config, disease_states):
        """Represents a disease model as a list of states.

        Each state may be any type, but it will be cast to a string and shortened into a single
        uppercase letter for brief representation in output.  This means, for example, passing in
        ['SUSCEPTIBLE', 'INFECTED', 'DEAD'] would result in the single-letter codes 'S', 'I', and
        'D'.
        """

        super().__init__(config)
        self.states             = disease_states
        self.states_letter_dict = {DiseaseModel.letter_for_state(s): s for s in disease_states}

        # Ensure state letter codes are unique.
        assert len(self.states_letter_dict) == len(self.states)

    def state_for_letter(self, letter):
        """Given a single uppercase letter, returns the disease state represented.  For example,
        given "I" this may return "INFECTED".

        Throws a KeyError if the value is not present in this disease model.
        """

        return self.states_letter_dict[letter]

    @staticmethod
    def letter_for_state(state):
        """Given a state type, return the uppercase letter that represents it in shortened
        output, e.g. "INFECTED" would return "I".

        These uppercase letter codes are guaranteed unique by the constructor of this class.
        """

        return str(state)[0].upper()

    # pylint: disable=no-self-use
    def initialise_agents(self, world):
        """Create initial health states for agents on a world.

        Operates on Agent list in place (does not return a value)"""
        # pylint: disable=unused-argument

        log.warning("STUB: initialise_agents in disease.py")

    ## pylint: disable=no-self-use
    #def get_health_transitions(self, t, sim, agent_updates):
    #    """Return a list of health transitions agents should enact this tick.
#
#    #    Each health transition should be a tuple containing an agent and the state to transition
     #   to: (agent, 'INFECTED').  This is expected to be the main simulation code managing health
     #   state transitions according to the disease being modelled, and is called within the
     #   main simulation loop.
#
#        This is in the form of a list of tuples (agent, health_state)"""
#        # pylint: disable=unused-argument
#
#        log.warning("STUB: get_health_transitions in disease.py")
