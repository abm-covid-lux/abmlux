import os
import psutil

BYTES_IN_A_GIB = 1.074e+9

def flatten(arr):
    """Flatten a list of lists, returning a single flat list."""

    return [item for sublist in arr for item in sublist]


def get_memory_usage():
    """Returns the current process' memory usage in bytes"""

    process = psutil.Process(os.getpid())
    return process.memory_info().rss  # in bytes

def print_memory_usage():
    byts = get_memory_usage()

    print(f"Current memory usage: {byts / BYTES_IN_A_GIB:.2f}GiB")
