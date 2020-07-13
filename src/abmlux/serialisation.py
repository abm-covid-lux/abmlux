"""Module responsible for reading and writing data to a serialised form.

This is used primarily to store/load intermediate results within the system."""

import sys
import pickle
import logging

log = logging.getLogger("serialisation")

def write_to_disk(obj, output_filename):
    """Write an object to disk at the filename given.

    Parameters:
        obj (python object):The object to write to disk
        output_filename (str):The filename to write to.  Files get overwritten
                              by default.

    Returns:
        None
    """

    log.info("Writing to %s...", output_filename)
    with open(output_filename, 'wb') as fout:
        pickle.dump(obj, fout, protocol=pickle.HIGHEST_PROTOCOL)


def read_from_disk(input_filename):
    """Read an object from disk from the filename given.

    Parameters:
        input_filename (str):The filename to read from.

    Returns:
        obj(Object):The python object read from disk
    """

    log.info('Reading data from %s...', input_filename)
    with open(input_filename, 'rb') as fin:
        payload = pickle.load(fin)

    return payload
