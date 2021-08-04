# ABMLUX
![Integration](https://github.com/abm-covid-lux/abmlux/workflows/Integration/badge.svg?branch=master)
![Pytest](https://github.com/abm-covid-lux/abmlux/workflows/Pytest/badge.svg)
![Pylint](https://github.com/abm-covid-lux/abmlux/workflows/Pylint/badge.svg)
[![CodeFactor](https://www.codefactor.io/repository/github/abm-covid-lux/abmlux/badge?s=006dc8f386c6ea6d2a7a90377ff30fcf15328919)](https://www.codefactor.io/repository/github/abm-covid-lux/abmlux)

This is a deterministic agent-based model of COVID-19 spread, initially designed for Luxembourg but applicable to other countries where sufficient agent data are available.

![ABMLUX Logo](abmlux_logo.jpg)


## Overview
This model relies on time use survey data to automate the behaviour of agents.  Map, activity, disease, and intervention models are all modular and a number of alternative modules are bundled with the main distribution.  Scenarios for the model are configured using YAML, and a [comprehensive sample scenario] is provided in this repository.

The code is pure python, and has been developed with readability and maintainability in mind.

The ABMlux model has been used for the preprint Thompson, J. and Wattam, S. "Estimating the impact of interventions against COVID-19: from lockdown to vaccination", 2021, https://doi.org/10.1101/2021.03.21.21254049.

### Input Data
Input data are defined per-scenario in the [Scenarios](Scenarios/) directory.  A single [YAML configuration file](Scenarios/Luxembourg/config.yaml) specifies exact data locations and parameters for the simulation.  This file is heavily commented, and the example contains a very detailed use-case for all available modules.

### Output Data
Output data is stored in a separate [output respository](https://github.com/abm-covid-lux/output).

## Requirements

 * python 3.9

## Usage

 * `pip install .`
 * `abmlux Scenarios/Luxembourg/config.yaml`

## Testing
To test:

    pip install .[test]
    pytest

## Docs
To generate documentation:

    pip install pdoc
    pdoc --html --overwrite --html-dir docs abmlux

There are a number of interfaces defined internally (e.g. DiseaseModel), which form the basis for pluggable modules through inheritance.  In addition to this, components communicate with the simulation engine via a messagebus, sending messages of two types:

 * _intent_ to change state, e.g. 'I wish to change this agent's location to xxx'
 * _action_ notifications updating the state of the world, e.g. 'Agent xxx has moved to location yyy'

Though it is possible to write new events, the [existing list of event types is documented here](docs/events.md).

## Citing This Work
If you publish using technology from this repository, please [give us a citation](https://www.medrxiv.org/content/10.1101/2021.03.21.21254049v1), using this handy BibTeX:

    @article {Thompson2021.03.21.21254049,
        author = {Thompson, James and Wattam, Stephen},
        title = {Estimating the impact of interventions against COVID-19: from lockdown to vaccination},
        elocation-id = {2021.03.21.21254049},
        year = {2021},
        doi = {10.1101/2021.03.21.21254049},
        publisher = {Cold Spring Harbor Laboratory Press},
        URL = {https://www.medrxiv.org/content/early/2021/03/26/2021.03.21.21254049},
        eprint = {https://www.medrxiv.org/content/early/2021/03/26/2021.03.21.21254049.full.pdf},
        journal = {medRxiv}
    }


## License
<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/"><img alt="Creative Commons Licence" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/">Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License</a>.

Read the full text for details, but basically this means:
 * No commercial exploitation ([contact us](https://www.abmlux.org) for another license in this case);
 * You must re-publish the source if you modify the application.

We would like this work to be useful to non-profit and academic users without significant effort.  If the license is an impediment to you using the work, please get in touch with us to discuss other licensing options.
