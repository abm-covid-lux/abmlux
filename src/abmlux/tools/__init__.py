"""Package abmlux.tools contains interactive tools for examining the simulation state and
performing various tasks such as visualisation and data export"""

import importlib

import logging

log = logging.getLogger("tools")

def get_tool_module(tool_name):
    """Dynamically instantiates a module from abmlux.tools, returning the module
    itself."""

    module_name = "abmlux.tools." + tool_name
    log.debug("Dynamically loading module name '%s'", module_name)
    mod = importlib.import_module(module_name)

    return mod
