#!/bin/bash


./density_model.py "$1"
./network_model.py "$1"
./markov_model.py "$1"
./abm.py "$1"


