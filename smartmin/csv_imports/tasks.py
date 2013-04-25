import StringIO
from smartmin import class_from_string
from django.utils import timezone
from .models import ImportTask
from time import sleep

from celery.task import task

@task(track_started=True)
def csv_import(task_id):  #pragma: no cover
    from django.db import transaction

    # there is a possible race condition between this task starting
    # so we have a bit of loop here to fetch the task
    tries = 0
    while tries < 5:
        try:
            task = ImportTask.objects.get(pk=task_id)
        except Exception as e:
            # this object just doesn't exist yet, sleep a bit then try again
            tries+=1
            if tries >= 5:
                raise e
            else:
                sleep(1)

    transaction.enter_transaction_management()
    transaction.managed()

    log = StringIO.StringIO()

    try:
        task.task_id = csv_import.request.id
        task.log("Started import at %s" % timezone.now())
        task.log("--------------------------------")
        task.save()

        transaction.commit()

        model = class_from_string(task.model_class)
        records = model.import_csv(task, log)

        task.log(log.getvalue())
        task.log("Import finished at %s" % timezone.now())
        task.log("%d record(s) added." % len(records))

        transaction.commit()

    except Exception as e:
        transaction.rollback()

        import traceback
        traceback.print_exc(e)

        task.log("\nError: %s\n" % e)
        task.log(log.getvalue())
        transaction.commit()

        raise e

    finally:
        transaction.leave_transaction_management()

    return task
