
import random

# TODO: can probably speed this up with a bitmap or similar
def multinoulli(problist):
    """Sample at random from a list of n options with given probabilities.

    Identical to 'roulette wheel' random selection.

    problist: a list of n items, each of which is a weight"""

    # Convert to a list if we've been handed a pandas dataframe
    # or someting else with an index
    if not isinstance(problist, list):
        problist = list(problist)

    p = random.randint(1, sum(problist))
    summ = 0
    for i in range(len(problist)):
        summ = summ + problist[i]
        if summ >= p:
            return i

