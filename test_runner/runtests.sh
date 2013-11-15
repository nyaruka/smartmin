#!/bin/sh

cd ..
python setup.py develop
pip install django-nose
pip install coverage
pip install django-celery

cd test-runner
python manage.py test blog -s --pdb --noinput --with-coverage --cover-package=smartmin --cover-html-dir=../coverage-report --cover-html


