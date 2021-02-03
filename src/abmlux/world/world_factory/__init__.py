"""World factories build a world upon a map.

Worlds comprise locations on a map with agents assigned to the locations in various ways.

They provide a set of data for the simulation to run upon, i.e. activity models will choose what
agents should do based on their world, and locations will be chosen from the world by the
movement model.

This world representation forms the basis of numerous indexing steps later on, offering
a way to boost performance over an ad-hoc association of locations and agents.
"""

from abmlux.world import World

class WorldFactory:
    """Generic world factory that outputs a World object."""

    def get_world(self) -> World:
        """Gets world"""
        pass
