import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_runner.settings")

from django.conf import settings  # noqa

app = Celery("test_runner")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
