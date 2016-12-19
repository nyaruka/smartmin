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
    task_obj = ImportTask.objects.get(pk=task_id)
    log = StringIO()

    task_obj.task_id = csv_import.request.id
    task_obj.task_status = ImportTask.RUNNING
    task_obj.log("Started import at %s" % timezone.now())
    task_obj.log("--------------------------------")
    task_obj.save()

    try:
        with transaction.atomic():
            model = class_from_string(task_obj.model_class)
            records = model.import_csv(task_obj, log)
            task_obj.task_status = ImportTask.SUCCESS
            task_obj.save()

            task_obj.log(log.getvalue())
            task_obj.log("Import finished at %s" % timezone.now())
            task_obj.log("%d record(s) added." % len(records))

    except Exception as e:
        import traceback
        traceback.print_exc(e)

        task_obj.task_status = ImportTask.FAILURE

        task_obj.log("\nError: %s\n" % e)
        task_obj.log(log.getvalue())
        task_obj.save()

        raise e

    return task_obj
