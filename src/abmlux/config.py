
import os
import os.path as osp
import yaml




class Config:

    def __init__(self, filename):
        print(f"Loading config from {filename}...")

        self.conf    = Config.load_config(filename)
        self.dirname = osp.dirname(filename)

    def __len__(self):
        return len(self.conf)

    def __getitem__(self, key):
        return self.conf[key]

    def __missing__(self, key):
        return self.conf.__missing__(key)

    def __contains__(self, key):
        return self.conf.__contains__(key)

    def filepath(self, key, ensure_exists=False):
        """Return the value at 'key' but as a filepath.

        Filepaths in config are relative to the basedir,
        unless they are specified as absolute (e.g. they
        have a leading slash or drive letter"""

        full_path = osp.join(self.dirname, self[key])

        # Ensure the file directory exists
        if ensure_exists:
            os.makedirs(osp.dirname(full_path), exist_ok=True)

        return full_path

    @staticmethod
    def load_config(filename):
        with open(filename) as fin:
            return yaml.load(fin, Loader=yaml.FullLoader)



