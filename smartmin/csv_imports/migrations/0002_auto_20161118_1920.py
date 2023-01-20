from django.db import migrations, models

import smartmin.csv_imports.models


class Migration(migrations.Migration):

    dependencies = [
        ("csv_imports", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="importtask",
            name="csv_file",
            field=models.FileField(
                help_text="A comma delimited file of records to import",
                upload_to=smartmin.csv_imports.models.generate_file_path,
                verbose_name="Import file",
            ),
        ),
    ]
