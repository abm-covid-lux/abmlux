

class TestDistributionInterpolate:
    """Tests the DistributionInterpolate function in abmlux.density_model"""

    def test_distribution_interpolate():
        """Ensure the total popultion sum is invariant for a test distribution"""
    
        height = np.random.randint(10)
        width = np.random.randint(10)
        
        res_fact = 2*np.random.randint(10)
    
        test_distribution = np.random.randint(0, 100, (height,width))

        print(test_distribution)    

        distribution_new = distribution_interpolate(test_distribution,res_fact)

        print(distribution_new)

        # Print the two popultion sums, which upto floating point error should be equal
        print(np.sum(test_distribution),np.sum(distribution_new))
