#!/bin/bash

pip freeze | grep -v "^-e" | xargs pip uninstall -y
pip install -U pip
pip install -U setuptools wheel
pip install -U APScheduler fastapi uvicorn[standard] pandas python-multipart pm4py psycopg[binary] sqlalchemy tomli
pip freeze > requirements-temp.txt
sed "/^pkg-resources==0.0.0$/d" requirements-temp.txt > requirements.txt
rm requirements-temp.txt
