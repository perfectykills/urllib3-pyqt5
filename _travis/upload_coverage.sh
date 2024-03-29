#!/bin/bash

set -exo pipefail

if [[ -e .coverage ]]; then
    python3.6 -m pip install codecov
    python3.6 -m codecov --env TRAVIS_OS_NAME,NOX_SESSION
fi
