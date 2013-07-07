#! /bin/bash

set -e
set -x

python -m unittest discover -s tvdbpy/ -v
