import datetime
from django.db import models, transaction
from smartmin import class_from_string

from smartmin.models import SmartModel

class ImportTask(SmartModel):
    csv_file = models.FileField(upload_to="csv_imports", verbose_name="Import file", help_text="A comma delimited file of records to import")
    model_class = models.CharField(max_length=255, help_text="The model we are importing for")
    import_log = models.TextField()
    task_id = models.CharField(null=True, max_length=64)

    def start(self):
        from .tasks import csv_import
        self.log("Queued import at %s" % datetime.datetime.now())
        result = csv_import.delay(self)
        self.task_id = result.task_id
        self.save()

    def done(self):
        from .tasks import csv_import
        if self.task_id:
            result = csv_import.AsyncResult(self.task_id)
            return result.ready()

    def status(self):
        from .tasks import csv_import
        status = "PENDING"
        if self.task_id:
            result = csv_import.AsyncResult(self.task_id)
            status = result.state
        return status

    def log(self, message):
        self.import_log += "%s\n" % message
        self.modified_on = datetime.datetime.now()
        self.save()

    def __unicode__(self):
        return "%s Import" % class_from_string(self.model_class)._meta.verbose_name.title()
