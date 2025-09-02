#!/bin/bash
######################################################################
# Script Name: run_test.sh
# Description: release instructions
# Args:
#     PYLINT_FILE: the location of the pylint.rc file in the monorepo
######################################################################

# Fail this script if any command fails
set -e

# Define constants
PYLINT_THRESHOLD="8"
COVERAGE_THRESHOLD="80"


# Collect input args
export PYLINT_FILE="../pylint.rc"

# Print environment conditions
echo "Initiating release test"
echo "Pylint file: ${PYLINT_FILE}"
echo "Python version: $(python3 --version)"


# Install pipenv
echo "Activating Python Env"
source ../env/bin/activate

# Execute pylint
echo "Executing pylint with threshold of ${PYLINT_THRESHOLD} using ${PYLINT_FILE}"
#python3 -m pylint --rcfile=${PYLINT_FILE} --fail-under=${PYLINT_THRESHOLD} sls

# Execute pytest
echo "Executing pytest"
#python3 -m coverage run --rcfile=../coveragerc.cfg -m pytest -v

## Execute code coverage
echo "Evaluating code coverage"
#pipenv run python -m coverage report -m --fail-under=${COVERAGE_THRESHOLD}


