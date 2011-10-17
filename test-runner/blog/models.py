from django.db import models
from smartmin.models import SmartModel, ActiveManager

class Post(SmartModel):
    title = models.CharField(max_length=128,
                             help_text="The title of this blog post, keep it relevant")
    body = models.TextField(help_text="The body of the post, go crazy")
    order = models.IntegerField(help_text="The order for this post, posts with smaller orders come first")
    tags = models.CharField(max_length=128,
                            help_text="Any tags for this post")


    objects = models.Manager()
    active = ActiveManager()
    
    def __unicode__(self):
        return self.title


class Category(SmartModel):
    name = models.SlugField(max_length=64, unique=True,
                            help_text="The name of this category")

