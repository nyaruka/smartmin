import StringIO
from smartmin import class_from_string
from django.utils import timezone
from .models import ImportTask
from time import sleep
from distutils.version import StrictVersion
import django

from celery.task import task

@task(track_started=True)
def csv_import(task_id):  #pragma: no cover
    from django.db import transaction

    # there is a possible race condition between this task starting
    # so we have a bit of loop here to fetch the task
    tries = 0
    task = None
    while tries < 5 and not task:
        try:
            task = ImportTask.objects.get(pk=task_id)
        except Exception as e:
            # this object just doesn't exist yet, sleep a bit then try again
            tries+=1
            if tries >= 5:
                raise e
            else:
                sleep(1)

    log = StringIO.StringIO()

    if StrictVersion(django.get_version()) < StrictVersion('1.6'):

        transaction.enter_transaction_management()
        transaction.managed()

        try:
            task.task_id = csv_import.request.id
            task.log("Started import at %s" % timezone.now())
            task.log("--------------------------------")
            task.save()

            transaction.commit()

            model = class_from_string(task.model_class)
            records = model.import_csv(task, log)
            task.save()

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

    else:

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
