
import random

import pytest

import abmlux.random_tools as rt

class TestRandomTools:

    def test_random_randrange_with_seed(self):

        EXPECTED = [3, 4, 1, 6, 7, 2, 1, 1, 0,
                    6, 8, 4, 0, 3, 8, 8, 5, 4, 2, 1]

        prng = random.Random()
        prng.seed(4)

        assert EXPECTED == [rt.random_randrange(prng, 10) for i in range(20)]

