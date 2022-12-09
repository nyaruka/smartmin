import os

from django.db import models
from django.utils import timezone
from django.utils.module_loading import import_string

from smartmin.models import SmartModel


def generate_file_path(instance, filename):

    file_path_prefix = "csv_imports/"

    name, extension = os.path.splitext(filename)

    if len(name) + len(extension) >= 100:
        name = name[: 100 - len(extension) - len(file_path_prefix)]

    return "%s%s%s" % (file_path_prefix, name, extension)


class ImportTask(SmartModel):
    PENDING = "PENDING"
    STARTED = "STARTED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"

    READY_STATES = [SUCCESS, FAILURE]

    csv_file = models.FileField(
        upload_to=generate_file_path,
        verbose_name="Import file",
        help_text="A comma delimited file of records to import",
    )

    model_class = models.CharField(max_length=255, help_text="The model we are importing for")

    import_params = models.TextField(blank=True, null=True, help_text="JSON blob of form parameters on task creation")

    import_log = models.TextField()

    import_results = models.TextField(blank=True, null=True, help_text="JSON blob of result values on task completion")

    task_id = models.CharField(null=True, max_length=64)

    task_status = models.CharField(max_length=32, default=PENDING)

    def start(self):
        from .tasks import csv_import

        self.log("Queued import at %s" % timezone.now())
        self.task_status = self.STARTED
        self.save(update_fields=["import_log", "task_status"])
        result = csv_import.delay(self.pk)
        self.task_id = result.task_id
        self.save(update_fields=["task_id"])

    def done(self):
        if self.task_id:
            return self.task_status in self.READY_STATES

    def status(self):
        return self.task_status

    def log(self, message):
        self.import_log += "%s\n" % message
        self.modified_on = timezone.now()
        self.save(update_fields=["import_log", "modified_on"])

    def __unicode__(self):
        return "%s Import" % import_string(self.model_class)._meta.verbose_name.title()
