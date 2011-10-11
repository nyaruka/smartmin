from django.db import models
from django.contrib.auth.models import User

class SmartModel(models.Model):
    """
    Useful abstract base class that adds the concept of something being active,
    having a user that created or modified the item and creation and modification
    dates.
    """
    is_active = models.BooleanField(default=True,
                                    help_text="Whether this item is active, use this instead of deleting")

    created_by = models.ForeignKey(User, related_name="%(class)s_creations",
                                   help_text="The user which originally created this item")    
    created_on = models.DateTimeField(auto_now_add=True,
                                      help_text="When this item was originally created")

    modified_by = models.ForeignKey(User, related_name="%(class)s_modifications",
                                    help_text="The user which last modified this item")
    modified_on = models.DateTimeField(auto_now=True,
                                       help_text="When this item was last modified")

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
