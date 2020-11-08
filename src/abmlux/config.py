"""Module supporting configuration of the simulation.

Configuration is set in a single YAML file, and used by many components throughout
the simulation process."""

import os
import os.path as osp
import yaml

class Config:
    """Represents the simulation configuration.

    This class behaves like a dict, but is read-only"""

    def __init__(self, filename):
        print(f"Loading config from {filename}...")

        self.conf    = Config.load_config(filename)
        self.dirname = osp.dirname(filename)

    def __len__(self):
        return len(self.conf)

    def __getitem__(self, key):
        if "." in key:
            return self._get(key)
        return self.conf[key]

    def __missing__(self, key):
        return self.conf.__missing__(key)

    def __contains__(self, key):
        return self.conf.__contains__(key)

    def filepath(self, key, path=None, *, ensure_exists=False):
        """Return the value at 'key' but as a filepath.
        Filepaths in config are relative to the basedir,
        unless they are specified as absolute (e.g. they
        have a leading slash or drive letter"""

        full_path = osp.join(self.dirname, self[key])

        # Add optional component
        if path is not None:
            full_path = osp.join(full_path, path)

        # Ensure the file directory exists
        if ensure_exists:
            os.makedirs(osp.dirname(full_path), exist_ok=True)

        return full_path

    def _get(self, dot_notation, obj=None):
        """Retrieve a key.key.key.1 string from nested dicts and lists"""

        if obj is None:
            obj = self

        # FIXME: handle 'spaces in keys'.more.more
        chunks = dot_notation.split(".")

        # Find the key
        key = chunks[0]
        if chunks[0] in "1234567890":
            key = int(key)

        value = obj[key]
        if len(chunks) > 1:
            return self._get(".".join(chunks[1:]), value)
        return value

    @staticmethod
    def load_config(filename):
        """Load a YAML config file and return the dict."""

        with open(filename) as fin:
            return yaml.load(fin, Loader=yaml.FullLoader)
