"""Test the basic config object used to load YAML"""

import os.path as osp
import tempfile

from abmlux.config import Config



SAMPLE_CONFIG = """---

list:
 - item_one
 - 1
 - 2.3

# comment
dict:
  key: value
  key2: 2.3
  key_list: [1,2,3]
"""

class TestConfig:
    """Test the config object, which makes YAML more usable as live config"""

    def test_load_config(self):
        """Ensure the config values are loaded as expected"""


        config = config_from_string(SAMPLE_CONFIG)


        assert len(config) == 2


    def test_get_simple(self):
        """Test basic retrieval using []."""

        config = config_from_string(SAMPLE_CONFIG)

        assert config['list'] == ['item_one', 1, 2.3]
        assert config['list'][1] == 1
        assert config['dict']['key'] == 'value'

    def test_get_compound(self):
        """Test dot notation retrieval"""

        config = config_from_string(SAMPLE_CONFIG)

        assert config['list.0'] == 'item_one'
        assert config['dict.key2'] == 2.3
        assert config['dict.key_list.2'] == 3

def config_from_string(config_string):
    """Write the string given to a file, then tell the config object to read from this file."""

    with tempfile.TemporaryDirectory() as tmpdirname:

        filename = osp.join(tmpdirname, 'config.yml')

        with open(filename, 'w') as fout:
            fout.write(config_string)

        config = Config(filename)

    return config
