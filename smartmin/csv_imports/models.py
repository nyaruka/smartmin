from __future__ import unicode_literals

from celery.result import EagerResult, AsyncResult
from django.db import models
from django.conf import settings
from django.utils import timezone
from smartmin import class_from_string
from smartmin.models import SmartModel


class ImportTask(SmartModel):
    csv_file = models.FileField(upload_to="csv_imports", verbose_name="Import file", help_text="A comma delimited file of records to import")

    model_class = models.CharField(max_length=255, help_text="The model we are importing for")

    import_params = models.TextField(blank=True, null=True, help_text="JSON blob of form parameters on task creation")

    import_log = models.TextField()

    import_results = models.TextField(blank=True, null=True, help_text="JSON blob of result values on task completion")

    task_id = models.CharField(null=True, max_length=64)

    def start(self):
        from .tasks import csv_import
        self.log("Queued import at %s" % timezone.now())
        self.save(update_fields=['import_log'])
        result = csv_import.delay(self.pk)
        self.task_id = result.task_id
        self.save(update_fields=['task_id'])

    def done(self):
        if self.task_id:
            if getattr(settings, 'CELERY_ALWAYS_EAGER', False):
                result = EagerResult(self.task_id, None, 'SUCCESS')
            else:
                result = AsyncResult(self.task_id)
            return result.ready()

    def status(self):
        status = "PENDING"
        if self.task_id:
            if getattr(settings, 'CELERY_ALWAYS_EAGER', False):
                result = EagerResult(self.task_id, None, 'SUCCESS')
            else:
                result = AsyncResult(self.task_id)
            status = result.state
        return status

    def log(self, message):
        self.import_log += "%s\n" % message
        self.modified_on = timezone.now()
        self.save(update_fields=['import_log', 'modified_on'])

    def __unicode__(self):
        return "%s Import" % class_from_string(self.model_class)._meta.verbose_name.title()
