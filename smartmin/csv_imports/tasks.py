from io import StringIO

from celery import shared_task

from django.utils import timezone
from django.utils.module_loading import import_string

from .models import ImportTask


@shared_task(track_started=True)
def csv_import(task_id):  # pragma: no cover
    task_obj = ImportTask.objects.get(pk=task_id)
    log = StringIO()

    task_obj.task_id = csv_import.request.id
    task_obj.task_status = ImportTask.RUNNING
    task_obj.log("Started import at %s" % timezone.now())
    task_obj.log("--------------------------------")
    task_obj.save()

    try:
        model = import_string(task_obj.model_class)
        records = model.import_csv(task_obj, log)
        task_obj.task_status = ImportTask.SUCCESS
        task_obj.save()

        task_obj.log(log.getvalue())
        task_obj.log("Import finished at %s" % timezone.now())
        task_obj.log("%d record(s) added." % len(records))

    except Exception as e:
        import traceback

        traceback.print_exc()

        task_obj.task_status = ImportTask.FAILURE

        task_obj.log("\nError: %s\n" % str(e))
        task_obj.log(log.getvalue())
        task_obj.save()

        raise e

    # give our model the opportunity to do any last finalization outside our transaction
    model.finalize_import(task_obj, records)

    return task_obj
