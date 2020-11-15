"""Wrapper around python's PRNG to ease the process of performing deterministic re-runs"""

from random import Random
import math
from functools import reduce
import logging
from typing import Sequence, TypeVar, MutableSequence, Any, Optional

log = logging.getLogger("random_tools")

# Type aliases for semantic-ness-ness
Probability = float
T = TypeVar('T')

def gammavariate(prng: Random, alpha: float, beta: float) -> Probability:
    """Sample gamma distributed random variable with pdf given by

                      x ** (alpha - 1) * math.exp(-x / beta)
        pdf(x) =      --------------------------------------.
                      math.gamma(alpha) * beta ** alpha

    That is, a gamma random variable with shape parameter alpha and scale parameter beta."""

    return prng.gammavariate(alpha, beta)


def random_randrange(prng: Random, stop: int) -> int:
    """Random randrange function"""

    return prng.randrange(stop)


def random_randrange_interval(prng: Random, start: int, stop: int) -> int:
    """Random randrange function"""

    return prng.randrange(start, stop)


def random_choice(prng: Random, sequence: Sequence[T]) -> T:
    """Random choice function"""

    return prng.choice(sequence)


def random_choices(prng: Random, population: Sequence[T], weights: Sequence[int],
                   sample_size: int) -> list[T]:
    """Random choices function"""

    return prng.choices(population, weights=weights, cum_weights=None, k=sample_size)


def random_sample(prng: Random, population: Sequence[T], k: int) -> list[T]:
    """Select k items from the population given."""

    return prng.sample(population, k)


def random_shuffle(prng: Random, x: MutableSequence[Any]) -> None:
    """Random shuffle function"""

    prng.shuffle(x)

def random_float(prng: Random, x: Probability) -> float:
    """Return random number between 0 and x"""

    return prng.random() * x

def multinoulli(prng: Random, problist: Sequence[Probability]) -> int:
    """Sample at random from a list of n options with given probabilities.

    Identical to 'roulette wheel' random selection.

    problist: a list of n items, each of which is a weight.

    Returns: The index number of the item chosen"""

    # Convert to a list if we've been handed a pandas dataframe
    # or someting else with an index
    # if not isinstance(problist, list):
    #     problist = list(problist)

    return prng.choices(range(len(problist)), problist)[0]


def multinoulli_dict(prng: Random, problist_dict: dict[T, Probability]) -> T:
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

    return prng.choices(list(problist_dict.keys()), weights)[0]


def multinoulli_2d(prng: Random, problist_arr: Sequence[Sequence[float]], 
                   marginals: Optional[Sequence[float]]=None) -> tuple[Probability, Probability]:
    """Sample from a 2D array of weights, returning
    an (x, y) tuple within the array.

    marginals --- optional list of weights for marginals.
    """

    if marginals is None:
        y_marginals: Sequence[float] = [sum(x) for x in problist_arr]
    else:
        y_marginals = marginals

    y = multinoulli(prng, y_marginals)
    x = multinoulli(prng, problist_arr[y])

    return x, y


def boolean(prng: Random, p: Probability) -> bool:
    """Return true with the probability given."""

    assert p >= 0
    assert p <= 1

    return prng.random() < p
