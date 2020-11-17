"""Utility functions used during CLI output and data management"""
import os
from zlib import adler32
import functools
import importlib
import logging

import matplotlib.cm as cm
import matplotlib.colors as colors
import psutil

BYTES_IN_A_GIB = 1.074e+9


log = logging.getLogger("utils")

def remove_dunder_keys(_dict) -> dict:
    """Remove __dunder__ keys from the dict.

    This is used where __type__ is used in configs to specify the type of class to be created,
    but we wish to use the rest of the data in the dict as args.  Essentially it's a method of
    in-band signalling."""

    new_dict = {k: v for k, v in _dict.items() \
                if not str(k).startswith("__") and not str(k).endswith("__")}
    return new_dict

def instantiate_class(module_base, module_path, *args, **kwargs):
    """Take a string and arguments and instantiate a class, returning it.

    Parameters:
        module_base (str): String showing the base module to instantiate upon, e.g. abmlux.reporters
        module_path (str): String containing module path, e.g. cli.TQDM
        *args, **kwargs: Passed to the constructor

    Returns: The class instantiated
    """

    # Instantiate the class itself
    log.debug("Instantiating class %s...", module_path)
    module_name = module_base + "." + ".".join(module_path.split(".")[:-1])
    class_name  = module_path.split(".")[-1]

    log.debug("Dynamically loading class '%s' from module name '%s'", module_name, class_name)
    mod = importlib.import_module(module_name)
    cls = getattr(mod, class_name)

    log.debug("Instantiating class %s with parameters %s and keyword parameters %s", \
              cls, args, kwargs)
    new_instance = cls(*args, **kwargs)

    return new_instance

def flatten(arr):
    """Flatten a list of lists, returning a single flat list.

    Parameters:
        arr: List of lists, or list-likes.
    """

    return [item for sublist in arr for item in sublist]


def get_memory_usage():
    """Returns the current process' memory usage in bytes"""

    process = psutil.Process(os.getpid())
    return process.memory_info().rss  # in bytes

def print_memory_usage():
    """Print memory usage to the terminal."""
    byts = get_memory_usage()

    print(f"Current memory usage: {byts / BYTES_IN_A_GIB:.2f}GiB")

@functools.lru_cache(maxsize=1024)
def string_as_mpl_colour(string, salt=0, scheme="nipy_spectral"):
    """Returns a matplotlib colour for the given string.

    Uses the adler32 hash to ensure the colour is always the same."""

    colour_map    = cm.get_cmap(scheme)
    location_hash = (adler32(string.encode("utf-8")) + salt) % 10000
    colour        = colour_map(location_hash / 10000)

    return colour

@functools.lru_cache(maxsize=1024)
def string_as_hex_colour(string, salt=0, scheme="nipy_spectral"):
    """Returns a hex string representing the string given.  Deterministic."""

    return colors.to_hex(string_as_mpl_colour(string, salt, scheme))
