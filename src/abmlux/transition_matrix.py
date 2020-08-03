"""Represents transitions from one state to another.

Used in the simulation to drive the main activity markov chain"""

import abmlux.random_tools as random_tools

class TransitionMatrix:
    """A basic transition matrix that stores a matrix and provides sampling
    capabilities"""

    def __init__(self, prng, classes):
        """Creates a new TransitionMatrix with the set of classes given.

        Parameters:
            classes (list):A list of classes.  A matrix will be created that is square,
                           using this list.
        """

        self.prng        = prng
        self.classes     = list(classes)
        self.transitions = {c: {c: 0 for c in classes} for c in classes}

        self.x_marginals = {c: 0 for c in classes}  # p[c -> _]

    def get_weight(self, c_from, c_to):
        """Return a raw weight value showing the transition weight
        from class c_from to class c_to

        raises KeyError if c_from or c_to are not in the matrix.

        Parameters:
            c_from (obj):The class to transition from
            c_to (obj):The class to transition to

        Returns:
            A number showing the raw weight for this cell
        """
        return self.transitions[c_from][c_to]

    def set_weight(self, c_from, c_to, weight):
        """Set the raw weight value representing the transition weight
        from class c_from to class c_to.

        This triggers recomputation of the matrix' marginal values,
        so calls to this may cost more than a simple dict update.

        raises KeyError if c_from or c_to are not in the matrix.
        raises ValueError if weight <0

        Parameters:
            c_from (obj):The class to transition from
            c_to (obj):The class to transition to
            weight (number):The weight this transition should have.
                            Must be greater than zero.
        """
        if weight < 0:
            raise ValueError("Weights must be above zero")
        self.transitions[c_from][c_to] = weight
        self._recompute_x_marginals(c_from)

    def add_weight(self, c_from, c_to, weight):
        """Add weight to a transition.

        Equivalent to set_weight(get_weight())

        This triggers recomputation of the matrix' marginal values,
        so calls to this may cost more than a simple dict update.

        raises KeyError if c_from or c_to are not in the matrix.
        raises ValueError if weight <0

        Parameters:
            c_from (obj):The class to transition from
            c_to (obj):The class to transition to
            weight (number):The weight this transition should increase by.
        """
        self.set_weight(c_from, c_to, self.get_weight(c_from, c_to) + weight)
        self._recompute_x_marginals(c_from)

    def p(self, c_from, c_to):
        """Returns the probability of transitioning from class
        c_from to class c_to.

        Parameters:
            c_from (obj):The class to transition from
            c_to (obj):The class to transition to

        Returns:
            Probability of transitioning from c_from to c_to (0<=p<=1)
        """
        if self.x_marginal(c_from) == 0:
            return 0
        return self.transitions[c_from][c_to] / self.x_marginal(c_from)

    def x_marginal(self, c_to):
        """Returns the marginal sum of the c_to row.

        Parameters:
            c_to (obj):The class to transition to

        Returns:
            Marginal sum of weights for c_to
        """
        return self.x_marginals[c_to]

    def _recompute_x_marginals(self, dirty_row=None):
        """Recalculates the internal marginals cache.

        If dirty_row is None, all rows will be recomputed,
        else only that row will be recomputed.

        Parameters:
            dirty_row (obj):The row to recompute.
        """

        if dirty_row is None:
            for cls in self.classes:
                self.x_marginals[cls] = sum(self.transitions[cls].values())
        else:
            self.x_marginals[dirty_row] = sum(self.transitions[dirty_row].values())

    def get_transition(self, c_from):
        """Makes a weighted random selection from the available
        transitions, returning the class to transition to.
        If no classes are available (marginal sum of weights == 0)
        a ValueError is thrown.

        Parameters:
            c_from (obj):The class to transition from.

        Returns:
            A class from the internal list that should be transitioned to next
        """

        if self.x_marginals[c_from] == 0:
            raise ValueError(f"No available transitions from current state "
                             f"({c_from} -> {self.transitions[c_from]})")

        return random_tools.multinoulli_dict(self.prng, self.transitions[c_from])



class SplitTransitionMatrix(TransitionMatrix):
    """A transition matrix that separates diagonal weights (the probability
    of transitioning from x->x.  This allows fast calculation of transition probabilities
    and a fast check to see if transition will occur at all."""

    # pylint disable=super-init-not-called
    def __init__(self, prng, classes):
        """Create a split transition matrix.

        Parameters:
            classes (list):A list of classes.  A matrix will be created that is square,
                           using this list.
        """

        self.prng    = prng
        self.classes = list(classes)

        self.diag               = {c: 0 for c in classes}
        self.transitions_nodiag = {c: {d: 0 for d in classes if d != c} for c in classes}

        self.x_marginals = {c: 0 for c in classes}  # p[c -> _]

    def get_weight(self, c_from, c_to):
        """Return a raw weight value showing the transition weight
        from class c_from to class c_to

        raises KeyError if c_from or c_to are not in the matrix.

        Parameters:
            c_from (obj):The class to transition from
            c_to (obj):The class to transition to

        Returns:
            A number showing the raw weight for this cell
        """
        if c_from == c_to:
            return self.diag[c_from]
        return self.transitions_nodiag[c_from][c_to]

    def set_weight(self, c_from, c_to, weight):
        """Set the raw weight value representing the transition weight
        from class c_from to class c_to.

        This triggers recomputation of the matrix' marginal values,
        so calls to this may cost more than a simple dict update.

        raises KeyError if c_from or c_to are not in the matrix.
        raises ValueError if weight <0

        Parameters:
            c_from (obj):The class to transition from
            c_to (obj):The class to transition to
            weight (number):The weight this transition should have.
                            Must be greater than zero.
        """
        if weight < 0:
            raise ValueError("Weights must be above zero")
        if c_from == c_to:
            self.diag[c_from] = weight
        else:
            self.transitions_nodiag[c_from][c_to] = weight
        self._recompute_x_marginals(c_from)

    def add_weight(self, c_from, c_to, weight):
        """Add weight to a transition.

        Equivalent to set_weight(get_weight())

        This triggers recomputation of the matrix' marginal values,
        so calls to this may cost more than a simple dict update.

        raises KeyError if c_from or c_to are not in the matrix.
        raises ValueError if weight <0

        Parameters:
            c_from (obj):The class to transition from
            c_to (obj):The class to transition to
            weight (number):The weight this transition should increase by.
        """
        self.set_weight(c_from, c_to, self.get_weight(c_from, c_to) + weight)
        self._recompute_x_marginals(c_from)

    def p(self, c_from, c_to):
        """Returns the probability of transitioning from class
        c_from to class c_to.

        Parameters:
            c_from (obj):The class to transition from
            c_to (obj):The class to transition to

        Returns:
            Probability of transitioning from c_from to c_to (0<=p<=1)
        """
        if self.x_marginal(c_from) == 0:
            return 0

        if c_from == c_to:
            w_trans = self.diag[c_from]
        else:
            w_trans = self.transitions_nodiag[c_from][c_to]

        return w_trans / self.x_marginal(c_from)

    def x_marginal(self, c_to):
        """Returns the marginal sum of the c_to row.

        Parameters:
            c_to (obj):The class to transition to

        Returns:
            Marginal sum of weights for c_to
        """
        return self.x_marginals[c_to]

    def _recompute_x_marginals(self, dirty_row=None):
        """Returns the marginal sum of the c_to row.

        Parameters:
            c_to (obj):The class to transition to

        Returns:
            Marginal sum of weights for c_to
        """

        if dirty_row is None:
            for cls in self.classes:
                self.x_marginals[cls] = sum(self.transitions_nodiag[cls].values()) + self.diag[cls]
        else:
            self.x_marginals[dirty_row] = sum(self.transitions_nodiag[dirty_row].values()) \
                                        + self.diag[dirty_row]

    def get_transition(self, c_from, force_transition=True):
        """Makes a weighted random selection from the available
        transitions, returning the class to transition to.
        If no classes are available (marginal sum of weights == 0)
        a ValueError is thrown.

        If force_transition is True, weights are adjusted to ignore
        the possiblity of transitioning from x->x (i.e. not transitioning
        to another class).  This is done to permit a use-case where get_no_trans
        is called to determine if transition will happen at all, then this method
        is called to determine what transition should happen.

        Parameters:
            c_from (obj):The class to transition from.

        Returns:
            A class from the internal list that should be transitioned to next
        """

        if self.x_marginals[c_from] == 0:
            raise ValueError(f"No available transitions from current state "
                             f"({c_from} -> {self.transitions_nodiag[c_from]})")

        # Select from the diagonal-less transition matrix
        if force_transition:
            return random_tools.multinoulli_dict(self.prng, self.transitions_nodiag[c_from])

        # Select from everything
        if self.get_no_trans(c_from):
            return c_from
        return random_tools.multinoulli_dict(self.prng, self.transitions_nodiag[c_from])

    def get_no_trans(self, c_from):
        """Probability of not transitioning.

        This is relatively high performance, and the obvious use-case is to check
        whether a transition should be made prior to calling get_transition with
        the force_transition parameter=True.

        Parameters:
            c_from (obj):The class to transition from.
        """
        return random_tools.boolean(self.prng, self.p(c_from, c_from))
