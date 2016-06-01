from __future__ import unicode_literals

from celery.task import task
from django.db import transaction
from django.utils import timezone
from smartmin import class_from_string
from .models import ImportTask

# python2 and python3 support
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


@task(track_started=True)
def csv_import(task_id):  # pragma: no cover
    task = ImportTask.objects.get(pk=task_id)
    log = StringIO()

    task.task_id = csv_import.request.id
    task.log("Started import at %s" % timezone.now())
    task.log("--------------------------------")
    task.save()

    try:
        with transaction.atomic():
            model = class_from_string(task.model_class)
            records = model.import_csv(task, log)
            task.save()

            task.log(log.getvalue())
            task.log("Import finished at %s" % timezone.now())
            task.log("%d record(s) added." % len(records))

    except Exception as e:
        import traceback
        traceback.print_exc(e)

        task.log("\nError: %s\n" % e)
        task.log(log.getvalue())

        raise e

    return task
