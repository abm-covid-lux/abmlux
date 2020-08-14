
import random
import math
from functools import reduce


def gammavariate(prng, alpha, beta):
    """Sample gamma distributed random variable with pdf given by

                      x ** (alpha - 1) * math.exp(-x / beta)
        pdf(x) =      --------------------------------------.
                      math.gamma(alpha) * beta ** alpha

    That is, a gamma random variable with shape parameter alpha and scale parameter beta."""

    return prng.gammavariate(alpha, beta)


def random_randrange(prng, stop):
    """Random randrange function"""

    return prng.randrange(stop)


def random_randrange_interval(prng, start, stop):
    """Random randrange function"""

    return prng.randrange(start,stop)


def random_choice(prng, sequence):
    """Random choice function"""

    return prng.choice(sequence)


def random_choices(prng, population, weights, sample_size):
    """Random choices function"""

    return prng.choices(population, weights=weights, cum_weights=None, k=sample_size)


def random_sample(prng, population, k):
    """Random sample function"""

    return prng.sample(population, k)


def random_shuffle(prng, x):
    """Random shuffle function"""

    return prng.shuffle(x)

def random_float(prng, x):
    """Return random number between 0 and x"""

    return prng.random() * x

def multinoulli(prng, problist):
    """Sample at random from a list of n options with given probabilities.

    Identical to 'roulette wheel' random selection.

    problist: a list of n items, each of which is a weight"""

    # Convert to a list if we've been handed a pandas dataframe
    # or someting else with an index
    # if not isinstance(problist, list):
    #     problist = list(problist)

    return prng.choices(range(len(problist)), problist)[0]


def multinoulli_dict(prng, problist_dict):
    """Sample from a key:value dict and return a key
    according to the weights in the values, i.e.:

     {'a': 4, 'b': 6} has a 60% chance of returning
     'b' and a 40% chance of returning 'a'."""

    return prng.choices(list(problist_dict.keys()), problist_dict.values())[0]


def multinoulli_2d(prng, problist_arr, marginals=None):
    """Sample from a 2D array of weights, returning
    an (x, y) tuple within the array.

    marginals --- optional list of weights for marginals.
    """

    y_marginals = marginals if marginals is not None else \
                  [sum(x) for x in problist_arr]
    y = multinoulli(prng, y_marginals)
    x = multinoulli(prng, problist_arr[y])

    return x, y


def boolean(prng, p):
    """Return true with the probability given."""

    assert p >= 0
    assert p <= 1

    return prng.random() < p
