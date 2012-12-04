from datetime import datetime

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from .models import PasswordHistory
import django.views.static

class ChangePasswordMiddleware:
    """
    Redirects all users to the password change form if we find that a user's
    password is expired.
    """
    def __init__(self):
        self.password_expire = getattr(settings, 'USER_PASSWORD_EXPIRATION', -1)

    def process_view(self, request, view, *args, **kwargs):
        newpassword_path = reverse('users.user_newpassword', args=[0])

        if (self.password_expire < 0 or not request.user.is_authenticated() or 
            view == django.views.static.serve or request.path == newpassword_path):
            return

        if PasswordHistory.is_password_expired(request.user):
            return HttpResponseRedirect(reverse('users.user_newpassword', args=['0']))
