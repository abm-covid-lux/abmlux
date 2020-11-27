"""Wrapper around python's PRNG to ease the process of performing deterministic re-runs"""

import random
import logging
import math
from typing import Sequence, TypeVar, MutableSequence, Any, Optional

log = logging.getLogger("random_tools")

# Type aliases for semantic-ness-ness
Probability = float
T = TypeVar('T')

class Random:
    """Wraps the python random classes as an abstraction layer over them,
    and offers a number of convenience methods"""

    def __init__(self, seed=None):
        self.prng = random.Random(seed)

    def gammavariate(self, alpha: float, beta: float) -> Probability:
        """Sample gamma distributed random variable with pdf given by

                        x ** (alpha - 1) * math.exp(-x / beta)
            pdf(x) =      --------------------------------------.
                        math.gamma(alpha) * beta ** alpha

        That is, a gamma random variable with shape parameter alpha and scale parameter beta."""

        return self.prng.gammavariate(alpha, beta)


    def random_randrange(self, stop: int) -> int:
        """Random randrange function"""

        return self.prng.randrange(stop)


    def random_randrange_interval(self, start: int, stop: int) -> int:
        """Random randrange function"""

        return self.prng.randrange(start, stop)


    def random_choice(self, sequence: Sequence[T]) -> T:
        """Random choice function"""

        return self.prng.choice(sequence)


    def fast_random_choice(self, sequence: Sequence[T], length: int) -> T:
        """Fast random choice function"""

        return sequence[math.floor(self.prng.random()*length)]


    def random_choices(self, population: Sequence[T], weights: Sequence[int],
                    sample_size: int) -> list[T]:
        """Random choices function"""

        return self.prng.choices(population, weights=weights, cum_weights=None, k=sample_size)


    def random_sample(self, population: Sequence[T], k: int) -> list[T]:
        """Select k items from the population given."""

        return self.prng.sample(population, k)


    def random_shuffle(self, x: MutableSequence[Any]) -> None:
        """Random shuffle function"""

        self.prng.shuffle(x)

    def random_float(self, x: Probability) -> float:
        """Return random number between 0 and x"""

        return self.prng.random() * x

    def multinoulli(self, problist: Sequence[Probability]) -> int:
        """Sample at random from a list of n options with given probabilities.

        Identical to 'roulette wheel' random selection.

        problist: a list of n items, each of which is a weight.

        Returns: The index number of the item chosen"""

        # Convert to a list if we've been handed a pandas dataframe
        # or someting else with an index
        # if not isinstance(problist, list):
        #     problist = list(problist)

        return self.prng.choices(range(len(problist)), problist)[0]


    def multinoulli_dict(self, problist_dict: dict[T, Probability]) -> T:
        """Sample from a key:value dict and return a key
        according to the weights in the values, i.e.:

        {'a': 4, 'b': 6} has a 60% chance of returning
        'b' and a 40% chance of returning 'a'."""

        if len(problist_dict) == 0:

            raise ValueError("Weighted selection not possible from 0 items")

        # Check all of our weights aren't 0
        weights = list(problist_dict.values())
        if sum(weights) == 0:
            log.warning("All items have 0 weight, choosing flat weights instead")
            weights = [1.0] * len(weights)

        return self.prng.choices(list(problist_dict.keys()), weights)[0]


    def multinoulli_2d(self, problist_arr: Sequence[Sequence[float]], 
                      marginals: Optional[Sequence[float]]=None) -> tuple[Probability, Probability]:
        """Sample from a 2D array of weights, returning
        an (x, y) tuple within the array.

        marginals --- optional list of weights for marginals.
        """

        if marginals is None:
            y_marginals: Sequence[float] = [sum(x) for x in problist_arr]
        else:
            y_marginals = marginals

        y = self.multinoulli(y_marginals)
        x = self.multinoulli(problist_arr[y])

        return x, y

    def boolean(self, probability_true: Probability) -> bool:
        """Return true with the probability given."""

        assert probability_true >= 0
        assert probability_true <= 1

        return self.prng.random() < probability_true
