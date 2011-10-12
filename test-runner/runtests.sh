#!/bin/sh

cd ..
python setup.py develop
pip install django-nose

cd test-runner
python manage.py test smartmin --noinput --with-coverage --cover-package=smartmin


