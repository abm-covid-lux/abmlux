
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

    def test_random_randrange_interval_with_seed(self):

        EXPECTED = [13, 14, 11, 16, 17, 12, 11, 11, 10,
                    16, 18, 14, 10, 13, 18, 18, 15, 14, 12, 11]

        prng = random.Random()
        prng.seed(4)

        assert EXPECTED == [rt.random_randrange_interval(prng, 10, 20) for i in range(20)]

    def test_random_choice(self):

        items = [1,2,3,8,7]
        prng = random.Random()

        for _ in range(10):
            assert rt.random_choice(prng, items) in items
