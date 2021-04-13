# ABMLUX
![Integration](https://github.com/abm-covid-lux/abmlux/workflows/Integration/badge.svg?branch=master)
![Pytest](https://github.com/abm-covid-lux/abmlux/workflows/Pytest/badge.svg)
![coverage](https://github.com/abm-covid-lux/abmlux/workflows/coverage/badge.svg)
![Pylint](https://github.com/abm-covid-lux/abmlux/workflows/Pylint/badge.svg)
[![CodeFactor](https://www.codefactor.io/repository/github/abm-covid-lux/abmlux/badge?s=006dc8f386c6ea6d2a7a90377ff30fcf15328919)](https://www.codefactor.io/repository/github/abm-covid-lux/abmlux)

This is an agent-based model of COVID-19 in Luxembourg.


![ABMLUX Logo](abmlux_logo.jpg)

## Overview

### Input Data
Defined per-scenario in Scenarios/Name/config.yaml.  See the yaml config file for descriptions of each of the parameters.

## Requirements

 * python 3.8

## Usage

 * `pip install .`
 * `abmlux Scenarios/Luxembourg/config.yaml`

To inspect the data post-hoc, and to run various other miscellaneous tools on the simulation state, there is a separate tool.  This must know which simulation you're running it on, as well as the subcommand you wish to run, e.g.:

    abmlux-tools Scenarios/Luxembourg/config.yml plot_locations

## Testing
To test:

    pip install .[test]
    pytest

## Docs
To generate documentation:

    pip install pdoc
    pdoc --html --overwrite --html-dir docs abmlux

## License
<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/"><img alt="Creative Commons Licence" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/">Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License</a>.

Read the full text for details, but basically this means:
 * No commercial exploitation ([contact us](https://www.abmlux.org) for another license in this case);
 * You must re-publish the source if you modify the application.

We would like this work to be useful to non-profit and academic users without significant effort.  If the license is an impediment to you using the work, please get in touch with us to discuss other licensing options.