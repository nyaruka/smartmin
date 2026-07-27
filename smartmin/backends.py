import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

logger = logging.getLogger(__name__)


class CaseInsensitiveBackend(ModelBackend):
    """
    Authenticates against settings.AUTH_USER_MODEL.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        try:
            user = User.objects.get(username__iexact=username)
            if user.check_password(password):
                return user
            else:
                return None
        except User.MultipleObjectsReturned:
            logger.warning("multiple users match username %r, refusing authentication", username)

            # burn a hash anyway so this path is indistinguishable from the others
            User().set_password(password)
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between a resolvable and an unresolvable user (#20760).
            User().set_password(password)
