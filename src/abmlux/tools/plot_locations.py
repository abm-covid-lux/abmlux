"""Plot locations using matplotlib"""

import logging

import matplotlib.pyplot as plt
from tqdm import tqdm

from abmlux.utils import string_as_mpl_colour

log = logging.getLogger("plot_locations")

DESCRIPTION = "Plots all locations in a world"""
HELP        = """[Location Type,LocationType,LocationType]"""

def main(state, types_to_show=None):
    """Plots locations using matplotlib"""

    config = state.config
    world = state.world

    # Choose which locations to show
    type_filter = config["locations"]
    if types_to_show is not None:
        type_filter = types_to_show.split(",")
    log.info("Showing location types: %s", type_filter)
    colours = {lt: string_as_mpl_colour(lt) for lt in type_filter}

    world.map.plot_border(plt)

    # Plot all the points
    for location_type in type_filter:
        log.info("Rendering locations of type '%s'...", location_type)

        for location in tqdm(world.locations_by_type[location_type]):
            x, y = location.coord
            plt.plot([x], [y], marker='o', markersize=1, color=colours[location_type])

    # Render a legend
    plt.legend(type_filter, scatterpoints=1)
    leg = plt.gca().get_legend()
    for i, location_type in enumerate(type_filter):
        leg.legendHandles[i].set_color(colours[location_type])

    # Show the plot
    plt.show()
