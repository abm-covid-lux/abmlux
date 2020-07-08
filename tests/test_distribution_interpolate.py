from pytest import approx
import numpy as np
from abmlux.density_model import distribution_interpolate

class TestDistributionInterpolate:
    """Tests the distribution_interpolate function in abmlux.density_model"""

    def test_distribution_interpolation_random_input(self):
        """Ensure the total popultion sum is invariant for a test distribution"""
    
        height = np.random.randint(1,11)
        width = np.random.randint(1,11)
        
        res_fact = 2*np.random.randint(1,11)
    
        test_distribution = np.random.randint(0, 100, (height,width))
        distribution_new = distribution_interpolate(test_distribution,res_fact)

        # Assert that the two popultion sums are equal, upto floating point error
        assert(np.sum(test_distribution)-np.sum(distribution_new)==approx(0))