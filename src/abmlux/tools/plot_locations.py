"""Plot locations using matplotlib"""

import os.path as osp
import logging

import matplotlib.pyplot as plt
from tqdm import tqdm

import abmlux
from abmlux.utils import string_as_mpl_colour
from abmlux.serialisation import read_from_disk


log = logging.getLogger("plot_locations")

DESCRIPTION = "Plots all locations in a network"""
HELP        = """[Location Type,LocationType,LocationType]"""

def main(config, types_to_show=None):
    """Plots locations using matplotlib"""

    network = read_from_disk(osp.join(config.filepath('working_dir', True),
                                      abmlux.NETWORK_FILENAME))

    # Choose which locations to show
    type_filter = config["locations"]
    if types_to_show is not None:
        type_filter = types_to_show.split(",")
    log.info("Showing location types: %s", type_filter)
    colours = {lt: string_as_mpl_colour(lt) for lt in type_filter}

    network.map.plot_border(plt)

    # Plot all the points
    for location_type in type_filter:
        log.info("Rendering locations of type '%s'...", location_type)

        for location in tqdm(network.locations_by_type[location_type]):
            x, y = location.coord
            plt.plot([x], [y], marker='o', markersize=1, color=colours[location_type])

    # Render a legend
    plt.legend(type_filter, scatterpoints=1)
    leg = plt.gca().get_legend()
    for i, location_type in enumerate(type_filter):
        leg.legendHandles[i].set_color(colours[location_type])

    # Show the plot
    plt.show()
