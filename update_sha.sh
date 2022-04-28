#!/bin/sh
PYTHON_FILE=$(find /var/app/current -name "update_sha.py")

echo "$PYTHON_FILE"

python3 "$PYTHON_FILE"