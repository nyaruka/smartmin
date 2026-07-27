from django.conf import settings
from django.utils import timezone


class TimezoneMiddleware:
    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        user_tz = getattr(settings, "USER_TIME_ZONE", None)

        if user_tz:
            timezone.activate(user_tz)
        else:
            timezone.deactivate()

        return self.get_response(request)
