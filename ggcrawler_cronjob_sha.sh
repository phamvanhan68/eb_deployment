#!/bin/sh
PYTHON_FILE=$(find /var/app/current -name "update_sha.py")
# Need to find it cause this shell script will be called an run at nother directory, not here
echo "$PYTHON_FILE"

python3 "$PYTHON_FILE"