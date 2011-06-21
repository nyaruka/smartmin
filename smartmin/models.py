from django.db import models
from django.contrib.auth.models import User

class SmartModel(models.Model):
    """
    Useful abstract base class that adds the concept of something being active,
    having a user that created or modified the item and creation and modification
    dates.
    """
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(User, related_name="%(class)s_creations")    
    created_on = models.DateTimeField(auto_now_add=True)

    modified_by = models.ForeignKey(User, related_name="%(class)s_modifications")
    modified_on = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class ActiveManager(models.Manager):
    """
    A manager that only selects items which are still active.
    """
    def get_query_set(self):
        """
        Where the magic happens, we automatically throw on an extra is_active = True to every filter
        """
        return super(ActiveManager, self).get_query_set().filter(is_active=True)
