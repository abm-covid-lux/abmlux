

import importlib

import logging

log = logging.getLogger("tools")

def get_tool_module(tool_name):
    module_name = "abmlux.tools." + tool_name
    log.debug("Dynamically loading module name '%s'", module_name)
    mod = importlib.import_module(module_name)

    return mod



