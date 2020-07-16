from pytest import approx
import numpy as np
from abmlux.map import DensityMap

class TestDistributionInterpolate:
    """Tests the distribution_interpolate function in abmlux.density_model"""

    def test_distribution_interpolation_random_input(self):
        """Ensure the total popultion sum is invariant for a test distribution"""

        height = np.random.randint(1,11)
        width = np.random.randint(1,11)


        # Build a density map with random inputs
        test_distribution = np.random.randint(0, 100, (height,width))
        dmap_a = DensityMap((0, 0), 10, 10, 1)
        for i, row in enumerate(test_distribution):
            for j, cell in enumerate(row):
                # print(f" => {i}, {j}, {cell}")
                dmap_a.set_density(i, j, cell)

        # Resample it at some resolution,
        # and assert that population sums remain the same due to normalisation
        for res_fact in [1,2,4,6,8,10,100]:
            dmap_b = dmap_a.resample(res_fact, True)
            assert(np.sum(dmap_a.density) - np.sum(dmap_b.density)==approx(0))
