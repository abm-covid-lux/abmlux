"""Tests the transition matrix class, used for the Markov activity model"""

import pytest

from abmlux.random_tools import Random
import abmlux.transition_matrix as tm

CLASSES = [1,2,3,4]
PRNG = Random()

class TestTransitionMatrix:
    """Tests the transition matrix"""

    def test_initial_probabilty(self):
        """Tests initial probability"""

        matrix = tm.TransitionMatrix(PRNG, CLASSES)

        # Everything should be zero
        for class_1 in CLASSES:
            for class_2 in CLASSES:
                assert matrix.get_weight(class_1, class_2) == 0
                assert matrix.p(class_1, class_2) == 0
                assert matrix.p(class_2, class_1) == 0

    def test_invalid_weights(self):
        """Checks for invalid weights"""

        matrix = tm.TransitionMatrix(PRNG, CLASSES)

        with pytest.raises(ValueError):
            matrix.set_weight(1, 1, -50)

        with pytest.raises(TypeError):
            matrix.set_weight(1, 1, "watermelon")
        with pytest.raises(TypeError):
            matrix.set_weight(1, 1, matrix)

    def test_invalid_classes(self):
        """Checks for invalid classes"""

        matrix = tm.TransitionMatrix(PRNG, CLASSES)

        with pytest.raises(KeyError):
            matrix.p("x", 1)
        with pytest.raises(KeyError):
            matrix.p(34, 1)


    def test_simple_probabilty(self):
        """Tests calculation of probabilities"""

        matrix = tm.TransitionMatrix(PRNG, CLASSES)

        # Add some weights to certain transitions
        matrix.set_weight(1, 1, 1)
        matrix.set_weight(1, 2, 1)
        matrix.set_weight(2, 1, 5)
        matrix.set_weight(2, 2, 5)

        # Check probabilities
        assert matrix.p(1, 2) == 0.5
        assert matrix.p(1, 1) == 0.5
        assert matrix.p(2, 1) == 0.5
        assert matrix.p(2, 1) == 0.5

    def test_one_path(self):
        """Tests calculation of probabilities"""

        matrix = tm.TransitionMatrix(PRNG, CLASSES)

        # Add some weights to certain transitions
        matrix.set_weight(1, 1, 1)
        matrix.set_weight(2, 2, 1)
        matrix.set_weight(3, 3, 22)
        matrix.set_weight(4, 4, 237827.2223)

        # Check probabilities
        assert matrix.p(1, 1) == 1
        assert matrix.p(2, 2) == 1
        assert matrix.p(3, 3) == 1
        assert matrix.p(4, 4) == 1

        assert matrix.p(2, 1) == 0
        assert matrix.p(1, 2) == 0

    def test_resampling_one_item(self):
        """Ensure the sampling always returns the one item it can"""

        matrix = tm.TransitionMatrix(PRNG, CLASSES)

        # Add some weights to certain transitions
        matrix.set_weight(1, 1, 1)
        matrix.set_weight(2, 3, 1)
        matrix.set_weight(3, 4, 22)
        matrix.set_weight(4, 1, 237827.2223)

        for _ in range(100):
            assert matrix.get_transition(1) == 1
            assert matrix.get_transition(2) == 3
            assert matrix.get_transition(3) == 4
            assert matrix.get_transition(4) == 1


class TestSplitTransitionMatrix:
    """Tests optimization feature for transition matrix"""

    def test_initial_probabilty(self):
        """Tests intitial probabilties"""

        matrix = tm.SplitTransitionMatrix(PRNG, CLASSES)

        # Everything should be zero
        for class_1 in CLASSES:
            for class_2 in CLASSES:
                assert matrix.get_weight(class_1, class_2) == 0
                assert matrix.p(class_1, class_2) == 0
                assert matrix.p(class_2, class_1) == 0

    def test_invalid_weights(self):
        """Check for invalid weights"""

        matrix = tm.SplitTransitionMatrix(PRNG, CLASSES)

        with pytest.raises(ValueError):
            matrix.set_weight(1, 1, -50)

        with pytest.raises(TypeError):
            matrix.set_weight(1, 1, "watermelon")
        with pytest.raises(TypeError):
            matrix.set_weight(1, 1, matrix)

    def test_invalid_classes(self):
        """Checks for invalid classes"""

        matrix = tm.SplitTransitionMatrix(PRNG, CLASSES)

        with pytest.raises(KeyError):
            matrix.p("x", 1)
        with pytest.raises(KeyError):
            matrix.p(34, 1)

    def test_invalid_transitions(self):
        """Check for invalid transitions"""

        matrix = tm.SplitTransitionMatrix(PRNG, CLASSES)

        with pytest.raises(ValueError):
            matrix.get_transition(1)

    def test_simple_probabilty(self):
        """Tests calculation of probabilities"""

        matrix = tm.SplitTransitionMatrix(PRNG, CLASSES)

        # Add some weights to certain transitions
        matrix.set_weight(1, 1, 1)
        matrix.set_weight(1, 2, 1)
        matrix.set_weight(2, 1, 5)
        matrix.set_weight(2, 2, 5)

        # Check probabilities
        assert matrix.p(1, 2) == 0.5
        assert matrix.p(1, 1) == 0.5
        assert matrix.p(2, 1) == 0.5
        assert matrix.p(2, 1) == 0.5

    def test_one_path(self):
        """Tests calculation of probabilities"""

        matrix = tm.SplitTransitionMatrix(PRNG, CLASSES)

        # Add some weights to certain transitions
        matrix.set_weight(1, 1, 1)
        matrix.set_weight(2, 2, 1)
        matrix.set_weight(3, 3, 22)
        matrix.set_weight(4, 4, 237827.2223)

        # Check probabilities
        assert matrix.p(1, 1) == 1
        assert matrix.p(2, 2) == 1
        assert matrix.p(3, 3) == 1
        assert matrix.p(4, 4) == 1

        assert matrix.p(2, 1) == 0
        assert matrix.p(1, 2) == 0

    def test_no_transition_prob(self):
        """Tests calculation of probabilities"""

        matrix = tm.SplitTransitionMatrix(PRNG, CLASSES)

        # Add some weights to certain transitions
        matrix.set_weight(1, 1, 1)
        matrix.set_weight(3, 3, 22)
        matrix.set_weight(4, 4, 237827.2223)

        # Check probabilities
        for _ in range(100):
            assert matrix.get_no_trans(1)
            assert matrix.get_no_trans(3)
            assert matrix.get_no_trans(4)

    def test_resampling_one_item(self):
        """Ensure the sampling always returns the one item it can"""

        matrix = tm.SplitTransitionMatrix(PRNG, CLASSES)

        # Add some weights to certain transitions
        matrix.set_weight(1, 1, 1)
        matrix.set_weight(2, 3, 1)
        matrix.set_weight(3, 4, 22)
        matrix.set_weight(4, 1, 237827.2223)

        for _ in range(100):
            assert matrix.get_transition(1, False) == 1
            assert matrix.get_transition(2, False) == 3
            assert matrix.get_transition(3, False) == 4
            assert matrix.get_transition(4, False) == 1

    def test_split_probabilities(self):
        """Tests calculation of probabilities"""

        matrix = tm.SplitTransitionMatrix(PRNG, CLASSES)

        # Add some weights to certain transitions
        matrix.set_weight(1, 1, 1)
        matrix.set_weight(1, 2, 1)

        assert matrix.p(1, 1) == 0.5
        assert matrix.p(1, 2) == 0.5
        for _ in range(100):
            assert matrix.get_transition(1, True) == 2
