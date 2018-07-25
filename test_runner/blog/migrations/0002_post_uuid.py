from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='uuid',
            field=models.CharField(max_length=36, default=uuid.uuid4, editable=False),
        ),
    ]
