"""Module supporting configuration of the simulation.

Configuration is set in a single YAML file, and used by many components throughout
the simulation process."""

# Allows classes to return their own type, e.g. from_file below
from __future__ import annotations

import os
import os.path as osp
import re
from typing import Optional, Any
import yaml

class Config:
    """Represents the simulation configuration.

    This class behaves like a dict, but is read-only"""

    INT_INDEX_FORMAT = re.compile(r'\d+')

    def __init__(self, filename: Optional[str]=None, _dict: Optional[dict]=None,
                 dirname: Optional[str]=None):
        print(f"Loading config from {filename}...")

        if _dict and filename:
            raise ValueError("Filename and dict value specified.  Please provide only one")

        # Handle optional arguments
        if filename is not None:
            self.conf = Config.load_config(filename)
            self.dirname = osp.dirname(filename)
            return

        # Fall through to handle the dict/dirname case
        self.conf = _dict or {}
        self.dirname = dirname or osp.dirname(osp.realpath(__file__))


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

    def subconfig(self, key: str) -> Config:
        """Create a Config object from a key in this config object, with the same directory
        settings."""

        obj = self[key]
        if not isinstance(obj, dict):
            raise ValueError(f"Cannot create child config from object that isn't dict (key: {key})")

        new_config = Config(_dict=obj, dirname=self.dirname)
        return new_config

    def filepath(self, key: str, path: Optional[str]=None, *, ensure_exists: bool=False):
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

    def _get(self, dot_notation: str, obj: Optional[Any]=None) -> Any:
        """Retrieve a key.key.key.1 string from nested dicts and lists.

        Note: does not support having dots in the keys themselves, as there is no way to escape
        this in the key syntax."""

        if obj is None:
            obj = self

        # FIXME: handle 'escaped dots . in keys'.more.more
        chunks = dot_notation.split(".")

        # If the key starts with a number, consider it an array index
        if Config.INT_INDEX_FORMAT.fullmatch(chunks[0]):
            value = obj[int(chunks[0])]
        else:
            value = obj[chunks[0]]

        if len(chunks) > 1:
            return self._get(".".join(chunks[1:]), value)
        return value

    @staticmethod
    def load_config(filename: str) -> dict:
        """Load a YAML config file and return the dict."""

        with open(filename) as fin:
            return yaml.load(fin, Loader=yaml.FullLoader)
