#!/bin/sh

cd ..
python setup.py develop

cd test-runner
python manage.py test smartmin --noinput


