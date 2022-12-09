from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FailedLogin",
            fields=[
                ("id", models.AutoField(verbose_name="ID", serialize=False, auto_created=True, primary_key=True)),
                ("failed_on", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.PROTECT)),
            ],
        ),
        migrations.CreateModel(
            name="PasswordHistory",
            fields=[
                ("id", models.AutoField(verbose_name="ID", serialize=False, auto_created=True, primary_key=True)),
                ("password", models.CharField(help_text="The hash of the password that was set", max_length=255)),
                ("set_on", models.DateTimeField(help_text="When the password was set", auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        help_text="The user that set a password", on_delete=models.PROTECT, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="RecoveryToken",
            fields=[
                ("id", models.AutoField(verbose_name="ID", serialize=False, auto_created=True, primary_key=True)),
                (
                    "token",
                    models.CharField(default=None, help_text="token to reset password", unique=True, max_length=32),
                ),
                ("created_on", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.PROTECT)),
            ],
        ),
    ]
