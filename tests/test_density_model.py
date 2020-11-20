"""Test module that reads density data from disk"""

import os
import os.path as osp
import unittest
import random

from abmlux.density_model import read_density_model_jrc
from abmlux.world.map import DensityMap

here = os.path.dirname(os.path.realpath(__file__))

class TestDensityModelJRC(unittest.TestCase):

    def test_loading_density_model(self):
        #def read_density_model_jrc(prng, filepath, country_code, res_fact, normalize, shapefilename,
        #                   shapefile_coordsystem):

        prng                  = random.Random()
        filepath              = osp.join(here, 'test_data/density_model/Population Distribution.csv')
        country_code          = "LU"
        res_fact              = 1
        normalize             = False
        shapefilename         = osp.join(here, 'test_data/density_model/LIMADM_CANTONS.shp')
        shapefile_coordsystem = 'epsg:2169'

        density_model = read_density_model_jrc(prng, filepath, country_code, res_fact, normalize,
                                               shapefilename, shapefile_coordsystem)

        # We want a density map
        assert isinstance(density_model, DensityMap)

        # From this data, we want the dimensions and such to be as checked below
        assert density_model.width() == 57000
        assert density_model.height() == 82000

        assert density_model.width_grid() == 57
        assert density_model.height_grid() == 82

        assert density_model.get_density(20,20) == 743
        assert density_model.get_density(18,72) == 226
