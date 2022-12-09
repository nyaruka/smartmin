import re
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.db import models
from django.utils import timezone


def is_password_complex(password):
    has_caps = re.search("[A-Z]+", password)
    has_lower = re.search("[a-z]+", password)
    has_digit = re.search("[0-9]+", password)

    if len(password) < 8 or (len(password) < 12 and (not has_caps or not has_lower or not has_digit)):
        return False
    else:
        return True


class RecoveryToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    token = models.CharField(max_length=32, unique=True, default=None, help_text="token to reset password")
    created_on = models.DateTimeField(auto_now_add=True)


class FailedLogin(models.Model):
    username = models.CharField(max_length=256)
    failed_on = models.DateTimeField(auto_now_add=True)


class PasswordHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, help_text="The user that set a password"
    )
    password = models.CharField(max_length=255, help_text="The hash of the password that was set")
    set_on = models.DateTimeField(auto_now_add=True, help_text="When the password was set")

    @classmethod
    def is_password_repeat(cls, user, password):
        password_window = getattr(settings, "USER_PASSWORD_REPEAT_WINDOW", -1)
        if password_window <= 0:
            return False

        # check their current password
        if check_password(password, user.password):
            return True

        # get all the passwords in the past year
        window_ago = timezone.now() - timedelta(days=password_window)
        previous_passwords = PasswordHistory.objects.filter(user=user, set_on__gte=window_ago)
        for previous in previous_passwords:
            if check_password(password, previous.password):
                return True

        return False

    @classmethod
    def is_password_expired(cls, user):
        password_expiration = getattr(settings, "USER_PASSWORD_EXPIRATION", -1)

        if password_expiration <= 0:
            return False

        # get the most recent password change
        last_password = PasswordHistory.objects.filter(user=user).order_by("-set_on")

        last_set = user.date_joined
        if last_password:
            last_set = last_password[0].set_on

        # calculate how long ago our password was set
        today = timezone.now()
        difference = today - last_set

        # return whether that is expired
        return difference.days > password_expiration
