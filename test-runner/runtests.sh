#!/bin/sh

cd ..
python setup.py develop
pip install django-nose
pip install coverage

cd test-runner
python manage.py test smartmin --noinput --with-coverage --cover-package=smartmin --cover-html-dir=../coverage-report --cover-html


