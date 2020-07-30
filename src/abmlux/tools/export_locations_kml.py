"""Renders the location network to KML"""

import os.path as osp
import logging

from tqdm import tqdm
import simplekml

import abmlux
from abmlux.serialisation import read_from_disk
from abmlux.utils import string_as_hex_colour

log = logging.getLogger("export_locations_kml")

DESCRIPTION = "Exports locations to a KML file"
HELP        = """FILENAME [Location Type,LocationType,LocationType]"""

def main(config, filename, types_to_show=None):
    """Exports locations to a KML file."""

    network = read_from_disk(config.filepath('working_dir', abmlux.NETWORK_FILENAME,
                                             ensure_exists=True))

    # Choose which locations to show
    type_filter = config["locations"]
    if types_to_show is not None:
        type_filter = types_to_show.split(",")
    log.info("Showing location types: %s", type_filter)

    kml = simplekml.Kml()

    # Plot all the points
    for location_type in type_filter:
        log.info("Rendering locations of type '%s'...", location_type)

        folder = kml.newfolder(name=location_type)
        colour = f"ff{string_as_hex_colour(location_type)[1:]}"
        for location in tqdm(network.locations_by_type[location_type]):
            # lon, lat optional height
            pnt = folder.newpoint(name=location.uuid, description=location_type,
                                  coords=[(location.wgs84[1], location.wgs84[0])])
            pnt.style.labelstyle.color = "00000000"
            pnt.style.iconstyle.color = colour

    # Output to file
    log.info("Writing to %s...", filename)
    with open(filename, 'w') as fout:
        fout.write(kml.kml())
