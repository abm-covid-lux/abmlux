"""Encapsulates Location configuration for the simulation"""

import logging

log = logging.getLogger("location_manager")

class LocationManager:
    """Maintains a list of location types"""

    def __init__(self, location_config):
        log.debug("Location types: %s", location_config)
        self.location_types = location_config

    def get_types(self) -> list[str]:
        """Return a list of location types"""
        return self.location_types
