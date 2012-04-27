import StringIO
from celery.task import task
from datetime import datetime
from smartmin import class_from_string

@task(track_started=True)
def csv_import(task):  #pragma: no cover
    from django.db import transaction

    transaction.enter_transaction_management()
    transaction.managed()

    log = StringIO.StringIO()

    try:
        task.task_id = csv_import.request.id
        task.log("Started import at %s" % datetime.now())
        task.log("--------------------------------")
        task.save()

        transaction.commit()

        model = class_from_string(task.model_class)
        records = model.import_csv(task.csv_file.file, task.created_by, log)

        task.log(log.getvalue())
        task.log("Import finished at %s" % datetime.now())
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
