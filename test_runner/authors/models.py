from django.db import models

from smartmin.models import SmartModel


class Author(SmartModel):
    name = models.CharField(max_length=128)
