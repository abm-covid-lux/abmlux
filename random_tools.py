
import random
import scipy.stats as sps

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

    choice = random.choices([False, True], [1.0-p, p])[0]
    return choice


#test = [[0,0,0], [2,2,2]]
#for i in range(10):
#    print(f"->{multinoulli_2d(test)}")

