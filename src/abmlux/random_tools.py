
import random
import scipy.stats as sps
import math
from functools import reduce

def random_seed(config):
    """Random seed function"""

    return random.seed(config)


def random_randrange(stop):
    """Random randrange function"""

    return random.randrange(stop)
    
def random_randrange_interval(start,stop):
    """Random randrange function"""

    return random.randrange(start,stop)


def random_choice(sequence):
    """Random choice function"""

    return random.choice(sequence)


def random_sample(population, k):
    """Random sample function"""

    return random.sample(population, k)


def random_shuffle(x):
    """Random shuffle function"""

    return random.shuffle(x)

def random_float(x):
    """Return random number between 0 and x"""

    return random.random() * x

def multinoulli(problist):
    """Sample at random from a list of n options with given probabilities.

    Identical to 'roulette wheel' random selection.

    problist: a list of n items, each of which is a weight"""

    # Convert to a list if we've been handed a pandas dataframe
    # or someting else with an index
    # if not isinstance(problist, list):
    #     problist = list(problist)

    return random.choices(range(len(problist)), problist)[0]


def multinoulli_dict(problist_dict):
    """Sample from a key:value dict and return a key
    according to the weights in the values, i.e.:

     {'a': 4, 'b': 6} has a 60% chance of returning
     'b' and a 40% chance of returning 'a'."""

    return random.choices(list(problist_dict.keys()), problist_dict.values())[0]


def multinoulli_2d(problist_arr, marginals=None):
    """Sample from a 2D array of weights, returning
    an (x, y) tuple within the array.

    marginals --- optional list of weights for marginals.
    """

    y_marginals = marginals if marginals is not None else \
                  [sum(x) for x in problist_arr]
    y = multinoulli(y_marginals)
    x = multinoulli(problist_arr[y])

    return x, y


def boolean(p):
    """Return true with the probability given."""

    assert p >= 0
    assert p <= 1

    return random.random() < p


#test = [[0,0,0], [2,2,2]]
#for i in range(10):
#    print(f"->{multinoulli_2d(test)}")


# ----------------------------------------------------------------------------------
# Weighted random sampling is one of the most-called things in the whole sim,
# and performance is very important.
#
# This source of weighted random classes is about four times faster than the stock
# random.choices()
# class FastWeightedRandomSource:

#     def __init__(self, classes, weights, max_bins=1_000_000, num_bins=None):
#         self.classes = classes
#         self.weights = weights

#         # Generate internal lookup table
#         self.lookup = []

#         # If all the weights are integers we can represent the weights
#         # with at most sum(weights) items (or fewer if there is a common
#         # divisor).
#         self.num_bins = max_bins if num_bins is None else num_bins
#         if sum([int(w) == w for w in weights]) == len(weights):
#             ideal_num_bins = sum(weights) / reduce(math.gcd, weights)
#             if ideal_num_bins <= max_bins:
#                 # print(f"Using precise binning (integer weights).  You're lucky!")
#                 self.num_bins = ideal_num_bins

#         self.divisor = sum(weights) / self.num_bins
#         # print(f"-> {self.divisor=}")
#         # print(f"Using {self.num_bins} bins with {self.divisor=}")

#         # Generate lookup table
#         for clas, weight in zip(classes, weights):
#             self.lookup += [clas] * int(weight / self.divisor)

#     def __next__(self):
#         return self.lookup[int(self.num_bins * random.random())]




# import code; code.interact(local=locals())


# classes = ["one", "two", "three", "four"]
# weights = [28, 400, 40, 40]

# fwrs = FastWeightedRandomSource(classes, weights)
# import time
# t1 = time.perf_counter()
# for i in range(10_000_000):
#     x = next(fwrs)
# t2 = time.perf_counter()
# print(f"Custom method: {t2 - t1}s")

# t3 = time.perf_counter()
# for i in range(10_000_000):
#     x = random.choices(classes, weights)
# t4 = time.perf_counter()
# print(f"random.choices: {t4 - t3}s")
