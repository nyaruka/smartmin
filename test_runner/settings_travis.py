from __future__ import unicode_literals

from .settings import *  # noqa


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'smartmin',
        'USER': 'postgres',
    },
}
