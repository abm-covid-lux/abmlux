# ABMLUX
This is an agent-based model of COVID-19 in Luxembourg.

![Pytest](https://github.com/abm-covid-lux/abmlux/workflows/Pytest/badge.svg)
![Pylint](https://github.com/abm-covid-lux/abmlux/workflows/Pylint/badge.svg)

[![Build Status](https://travis-ci.com/abm-covid-lux/abmlux.svg?token=kQRz83XUzT6dhmswrBbj&branch=master)](https://travis-ci.com/abm-covid-lux/abmlux)
[![CodeFactor](https://www.codefactor.io/repository/github/abm-covid-lux/abmlux/badge?s=006dc8f386c6ea6d2a7a90377ff30fcf15328919)](https://www.codefactor.io/repository/github/abm-covid-lux/abmlux)

## Overview

### Input Data
Defined per-scenario in Scenarios/Name/config.yaml.  See the yaml config file for descriptions of each of the parameters.

## Requirements

 * python 3.8

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

