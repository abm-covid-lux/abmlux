"""Produce a set of location plots, one for each time tick, showing population at each location"""

import os
import os.path as osp

from abmlux.reporter import Reporter
import matplotlib.pyplot as plt
import logging


class LocationPlots(Reporter):
    """Output multiple plots showing agent locations at each time step"""

    def __init__(self, dirname, types_to_show=None, figure_size=(10, 10), every_n=1):

        self.dirname     = dirname
        self.figure_size = figure_size
        self.every_n     = every_n

        os.makedirs(self.dirname, exist_ok=True)

        # Choose which locations to show
        self.type_filter = None
        if types_to_show is not None and len(types_to_show) > 0:
            self.type_filter = types_to_show.split(",")
        self.colours = None

    def start(self, sim):
        if self.type_filter is None:
            self.type_filter = sim.network.locations_by_type.keys()
        self.colours = {lt: LocationPlots.location_type_as_color(lt) for lt in self.type_filter}

    def iterate(self, sim):

        if sim.clock.t % self.every_n != 0:
            return

        network = sim.network

        fig = plt.gcf()
        fig.set_size_inches(self.figure_size[0], self.figure_size[1])

        # Plot all the points
        for location_type in self.type_filter:
            #log.info("Rendering locations of type '%s'...", location_type)
            for location in network.locations_by_type[location_type]:
                x, y = location.coord
                plt.plot([x], [y], marker='o', markersize=len(sim.attendees[location]),
                         color=self.colours[location_type])

        # Render a legend
        plt.legend(self.type_filter, scatterpoints=1, loc="upper right")
        ax = plt.gca()
        leg = ax.get_legend()
        for i, location_type in enumerate(self.type_filter):
            leg.legendHandles[i].set_color(self.colours[location_type])
        plt.title(f"t={sim.clock.t}, {sim.clock.now()}")

        fig.savefig(osp.join(self.dirname, f"{sim.clock.t:05}.png"))

    def stop(self, sim):
        pass

    @staticmethod
    def location_type_as_color(location_type):
        """Return a matplotlib colour"""

        colour_map    = plt.get_cmap('gist_rainbow')
        location_hash = abs(hash(location_type)) % 10000
        colour        = colour_map(location_hash / 10000)

        return colour
