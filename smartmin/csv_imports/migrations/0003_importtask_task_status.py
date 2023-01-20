from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("csv_imports", "0002_auto_20161118_1920"),
    ]

    operations = [
        migrations.AddField(
            model_name="importtask",
            name="task_status",
            field=models.CharField(default="PENDING", max_length=32),
        ),
    ]
