
import abmlux.random_tools as random_tools

class TransitionMatrix:

    def __init__(self, classes):

        self.classes     = list(classes)
        self.transitions = {c: {c: 0 for c in classes} for c in classes}

        self.x_marginals = {c: 0 for c in classes}  # p[c -> _]

    def get_weight(self, c_from, c_to):
        return self.transitions[c_from][c_to]

    def set_weight(self, c_from, c_to, weight):
        if weight < 0:
            raise ValueError("Weights must be above zero")
        self.transitions[c_from][c_to] = weight
        self._recompute_x_marginals(c_from)

    def p(self, c_from, c_to):
        """Returns the probability of transitioning from class
        c_from to class c_to."""
        if self.x_marginal(c_from) == 0:
            return 0
        return self.transitions[c_from][c_to] / self.x_marginal(c_from)

    def x_marginal(self, c_to):
        """Return the probability 0-1 of transitioning from
        this class to a given class."""
        return self.x_marginals[c_to]

    def add_weight(self, c_from, c_to, weight):
        self.set_weight(c_from, c_to, self.get_weight(c_from, c_to) + weight)
        self._recompute_x_marginals(c_from)

    def _recompute_x_marginals(self, dirty_row=None):
        """Recalculates the internal marginals cache"""

        if dirty_row is None:
            for c in self.classes:
                self.x_marginals[c] = sum(self.transitions[c].values())
        else:
            self.x_marginals[dirty_row] = sum(self.transitions[dirty_row].values())

    def get_transition(self, c_from):
        """Makes a weighted random selection from the available
        transitions, returning the class to transition to.
        If no classes are available (marginal sum of weights == 0)
        a ValueError is thrown."""

        if self.x_marginals[c_from] == 0:
            raise ValueError(f"No available transitions from current state ({c_from} -> {self.transitions[c_from]})")

        return random_tools.multinoulli_dict(self.transitions[c_from])



class SplitTransitionMatrix(TransitionMatrix):
    """A transition matrix that separates diagonal weights (the probability
    of transitioning from x->x.  This allows fast calculation of transition probabilities
    and a fast check to see if transition will occur at all."""

    def __init__(self, classes):

        self.classes     = list(classes)

        self.diag               = {c: 0 for c in classes}
        self.transitions_nodiag = {c: {d: 0 for d in classes if d != c} for c in classes}

        self.x_marginals = {c: 0 for c in classes}  # p[c -> _]

    def get_weight(self, c_from, c_to):
        if c_from == c_to:
            return self.diag[c_from]
        return self.transitions_nodiag[c_from][c_to]

    def set_weight(self, c_from, c_to, weight):
        if weight < 0:
            raise ValueError("Weights must be above zero")
        if c_from == c_to:
            self.diag[c_from] = weight
        else:
            self.transitions_nodiag[c_from][c_to] = weight
        self._recompute_x_marginals(c_from)

    def p(self, c_from, c_to):
        """Returns the probability of transitioning from class
        c_from to class c_to."""
        if self.x_marginal(c_from) == 0:
            return 0

        if c_from == c_to:
            w_trans = self.diag[c_from]
        else:
            w_trans = self.transitions_nodiag[c_from][c_to]

        return w_trans / self.x_marginal(c_from)

    def x_marginal(self, c_to):
        """Return the probability 0-1 of transitioning from
        this class to a given class."""
        return self.x_marginals[c_to]

    def add_weight(self, c_from, c_to, weight):
        self.set_weight(c_from, c_to, self.get_weight(c_from, c_to) + weight)
        self._recompute_x_marginals(c_from)

    def _recompute_x_marginals(self, dirty_row=None):
        """Recalculates the internal marginals cache"""

        if dirty_row is None:
            for c in self.classes:
                self.x_marginals[c] = sum(self.transitions_nodiag[c].values()) + self.diag[c]
        else:
            self.x_marginals[dirty_row] = sum(self.transitions_nodiag[dirty_row].values()) + self.diag[dirty_row]

    def get_transition(self, c_from, force_transition=True):
        """Makes a weighted random selection from the available
        transitions, returning the class to transition to.
        If no classes are available (marginal sum of weights == 0)
        a ValueError is thrown."""

        if self.x_marginals[c_from] == 0:
            raise ValueError(f"No available transitions from current state ({c_from} -> {self.transitions_nodiag[c_from]})")

        # Select from the diagonal-less transition matrix
        if force_transition:
            return random_tools.multinoulli_dict(self.transitions_nodiag[c_from])

        # Select from everything
        if self.get_no_trans(c_from):
            return c_from
        return random_tools.multinoulli_dict(self.transitions_nodiag[c_from])

    def get_no_trans(self, c_from):
        """Probability of not transitioning"""
        return random_tools.boolean(self.p(c_from, c_from))
