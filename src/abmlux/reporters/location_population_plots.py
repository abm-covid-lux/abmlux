"""Produce a set of location plots, one for each time tick, showing population at each location"""

import os
import os.path as osp
from zlib import adler32
# import logging

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from abmlux.reporter import Reporter
from abmlux.agent import HealthStatus


# FIXME: remove this in favour of parameters
LOCATION_TYPE_BLACKLIST = ["Outdoor", "Public Transport"]

class LocationPlots(Reporter):
    """Output multiple plots showing agent locations at each time step"""

    def __init__(self, dirname, types_to_show=None, health_to_show=None, figure_size=(10, 10), every_n=1):

        self.dirname     = dirname
        self.figure_size = figure_size
        self.every_n     = every_n

        os.makedirs(self.dirname, exist_ok=True)

        # Choose which health states to show
        self.health_filter = list(HealthStatus)
        if health_to_show is not None and len(health_to_show) > 0:
            self.health_filter = [HealthStatus[h] for h in health_to_show]
        self.health_state_label = ", ".join([h.name for h in self.health_filter])

        # Choose which locations to show
        self.type_filter = None
        if types_to_show is not None and len(types_to_show) > 0:
            self.type_filter = types_to_show.split(",")

        # To be populated the first time we see the sim
        self.colours = None
        self.legend_items = []

    def start(self, sim):
        if self.type_filter is None:
            self.type_filter = [x for x in list(sim.network.locations_by_type.keys())
                                if x not in LOCATION_TYPE_BLACKLIST]
        self.colours = {lt: LocationPlots.location_type_as_color(lt) for lt in self.type_filter}

        # Build a legend
        for location_type, colour in self.colours.items():
            self.legend_items.append(Line2D([0], [0], marker='o', color='w',
                                            label=location_type, markerfacecolor=colour, markersize=15))


    def iterate(self, sim):

        if sim.clock.t % self.every_n != 0:
            return

        network = sim.network

        plt.figure()

        # FIXME: make these discoverable by inspecting the current map
        # MAP_DIMENSIONS_COORD = 57000, 82000 # width, height
        # plt.xlim(0, MAP_DIMENSIONS_COORD[0])
        # plt.ylim(0, MAP_DIMENSIONS_COORD[1])
        # plt.axis('off')

        # FIXME: remove this or make it configurable
        # ax = plt.gca()
        # ax.imshow(plt.imread("luxembourg-bg.png"), extent=[0, MAP_DIMENSIONS_COORD[0], 0,
        #           MAP_DIMENSIONS_COORD[1]])

        fig = plt.gcf()
        fig.set_size_inches(self.figure_size[0], self.figure_size[1])

        # Plot all the points
        for location_type in self.type_filter:
            #log.info("Rendering locations of type '%s'...", location_type)
            for location in network.locations_by_type[location_type]:
                for health in self.health_filter:
                    if sim.agent_counts_by_health[health][location] > 0:
                        # print(f"-> {health} // {sim.agent_counts_by_health[health][location]}")
                        x, y = location.coord

                        # print(f"-> {x}, {y}")
                        plt.plot([x], [y], marker='o',
                                 markersize=sim.agent_counts_by_health[health][location],
                                 color=self.colours[location_type])

        # Render a legend
        plt.legend(handles=self.legend_items, loc="upper right")
        plt.title(f"Attendance; health_states={self.health_state_label}; t={sim.clock.t}; {sim.clock.now()}")

        fig.savefig(osp.join(self.dirname, f"{sim.clock.t:05}.png"))
        plt.close()

    def stop(self, sim):
        pass

    @staticmethod
    def location_type_as_color(location_type):
        """Return a matplotlib colour"""

        colour_map    = plt.get_cmap('nipy_spectral')
        location_hash = adler32(location_type.encode("utf-8")) % 10000
        colour        = colour_map(location_hash / 10000)

        return colour
