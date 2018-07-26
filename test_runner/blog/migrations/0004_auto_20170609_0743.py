from django.db import migrations, models
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0003_auto_20170223_0917'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='written_on',
            field=models.DateField(default=django.utils.timezone.now, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='post',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
    ]
