import json
import re
import zoneinfo
from datetime import datetime, timedelta

from django import template
from django.conf import settings
from django.template import TemplateSyntaxError
from django.urls import reverse
from django.utils import timezone

register = template.Library()


@register.simple_tag
def get_hostname():
    if settings.HOSTNAME:
        return settings.HOSTNAME
    return "localhost"


@register.simple_tag(takes_context=True)
def get_list_class(context, list):
    """
    Returns the class to use for the passed in list.  We just build something up
    from the object type for the list.
    """
    return "list_%s_%s" % (list.model._meta.app_label, list.model._meta.model_name)


def format_datetime(time):
    """
    Formats a date, converting the time to the user timezone if one is specified
    """
    user_time_zone = timezone.get_current_timezone()
    if time.tzinfo is None:
        time = time.replace(tzinfo=timezone.utc)
        user_time_zone = zoneinfo.ZoneInfo(getattr(settings, "USER_TIME_ZONE", "GMT"))

    time = time.astimezone(user_time_zone)
    return time.strftime("%b %d, %Y %H:%M")


@register.simple_tag(takes_context=True)
def get_value_from_view(context, field):
    """
    Responsible for deriving the displayed value for the passed in 'field'.

    This first checks for a particular method on the ListView, then looks for a method
    on the object, then finally treats it as an attribute.
    """
    view = context["view"]
    obj = None
    if "object" in context:
        obj = context["object"]

    value = view.lookup_field_value(context, obj, field)

    # it's a date
    if type(value) == datetime:
        return format_datetime(value)

    return value


@register.simple_tag(takes_context=True)
def get_value(context, obj, field):
    """
    Responsible for deriving the displayed value for the passed in 'field'.

    This first checks for a particular method on the ListView, then looks for a method
    on the object, then finally treats it as an attribute.
    """
    view = context["view"]
    value = view.lookup_field_value(context, obj, field)
    if type(value) == datetime:
        return format_datetime(value)

    return value


@register.simple_tag(takes_context=True)
def get_class(context, field, obj=None):
    """
    Looks up the class for this field
    """
    view = context["view"]
    return view.lookup_field_class(field, obj, "field_" + field)


@register.simple_tag(takes_context=True)
def get_label(context, field, obj=None):
    """
    Responsible for figuring out the right label for the passed in field.

    The order of precedence is:
       1) if the view has a field_config and a label specified there, use that label
       2) check for a form in the view, if it contains that field, use it's value
    """
    view = context["view"]
    return view.lookup_field_label(context, field, obj)


@register.simple_tag(takes_context=True)
def get_field_link(context, field, obj=None):
    """
    Determine what the field link should be for the given field, object pair
    """
    view = context["view"]
    return view.lookup_field_link(context, field, obj)


@register.simple_tag(takes_context=True)
def view_as_json(context):
    """
    Returns our view serialized as json
    """
    view = context["view"]
    return json.dumps(view.as_json(context))


@register.simple_tag(takes_context=True)
def ssl_url(context, url_name, args=None):
    path = reverse(url_name, args)
    if getattr(settings, "SESSION_COOKIE_SECURE", False):
        return "https://%s%s" % (settings.HOSTNAME, path)
    else:
        return path


@register.simple_tag(takes_context=True)
def non_ssl_url(context, url_name, args=None):
    path = reverse(url_name, args)
    if settings.HOSTNAME != "localhost":
        return "http://%s%s" % (settings.HOSTNAME, path)
    return path


@register.filter
def field(form, field):
    try:
        return form[field]
    except KeyError:
        return None


@register.filter(name="add_css")
def add_css(field, css):
    custom_attrs = field.field.widget.attrs

    if not custom_attrs.get("class", None):
        custom_attrs["class"] = css
    else:
        custom_attrs["class"] += " " + css

    return field.as_widget(attrs=custom_attrs)


@register.filter
def map(string, args):
    return string % args.__dict__


@register.filter
def gmail_time(dtime, now=None):
    if dtime.tzinfo is None:
        dtime = dtime.replace(tzinfo=timezone.utc)
        user_time_zone = zoneinfo.ZoneInfo(getattr(settings, "USER_TIME_ZONE", "GMT"))
        dtime = dtime.astimezone(user_time_zone)
    else:
        dtime = dtime.astimezone(timezone.get_current_timezone())

    if not now:
        now = timezone.now()

    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    twelve_hours_ago = now - timedelta(hours=12)

    if dtime > twelve_hours_ago:
        return "%d:%s %s" % (int(dtime.strftime("%I")), dtime.strftime("%M"), dtime.strftime("%p").lower())
    elif now.year == dtime.year:
        return "%s %d" % (dtime.strftime("%b"), int(dtime.strftime("%d")))
    else:
        return "%d/%d/%s" % (int(dtime.strftime("%d")), int(dtime.strftime("%m")), dtime.strftime("%y"))


@register.filter
def user_as_string(user):
    full_name = user.get_full_name()
    if full_name:
        return full_name
    else:
        return user.username


@register.filter
def field_help(view, field):
    """
    Returns the field help for the passed in field
    """
    return view.lookup_field_help(field)


@register.filter
def get(dictionary, key):
    """
    Simple dict lookup using two variables
    """
    if key in dictionary:
        return dictionary[key]
    else:
        return ""


@register.filter
def is_smartobject(obj):
    """
    Returns whether the passed in object is a smart object
    """
    return hasattr(obj, "is_active")


@register.filter
def field_orderable(view, field):
    """
    Returns whether the passed in field is orderable
    """
    return view.lookup_field_orderable(field)


class PDBNode(template.Node):
    """
    Woot woot, simple pdb debugging. {% pdb %}
    """

    def render(self, context):
        import pdb

        pdb.set_trace()  # noqa


@register.tag
def pdb(parser, token):
    return PDBNode()


@register.simple_tag(takes_context=True)
def getblock(context, prefix, suffix=None):
    key = prefix
    if suffix:
        key += str(suffix)

    if "blocks" not in context:
        raise TemplateSyntaxError("setblock/endblock can only be used with SmartView or it's subclasses")

    if key in context["blocks"]:
        return context["blocks"][key]
    else:
        return ""


def setblock(parser, token):
    args = token.split_contents()
    if len(args) < 2:
        raise TemplateSyntaxError("setblock tag takes one argument, the name of the block got: [%s]" % ",".join(args))

    key = "".join(args[1:])

    nodelist = parser.parse(("endsetblock",))
    parser.delete_first_token()
    return SetBlockNode(key, nodelist)


class SetBlockNode(template.Node):
    def __init__(self, key, nodelist):
        self.key = key
        self.nodelist = nodelist

    def render(self, context):
        if "blocks" not in context:
            raise TemplateSyntaxError("setblock/endblock can only be used with SmartView or it's subclasses")

        output = self.nodelist.render(context)
        context["blocks"][self.key] = output
        return ""


# register our tag
setblock = register.tag(setblock)


@register.inclusion_tag("smartmin/field.html", takes_context=True)
def render_field(context, field):
    form = context["form"]
    view = context["view"]

    readonly_fields = view.derive_readonly()

    # check that this field exists in our form, either as a real field or as a readonly one
    if field not in form.fields and field not in readonly_fields:
        raise TemplateSyntaxError("Error: No field '%s' found in form to render" % field)

    inclusion_context = dict(field=field, form=context["form"], view=context["view"], blocks=context["blocks"])
    if "object" in context:
        inclusion_context["object"] = context["object"]

    return inclusion_context


@register.simple_tag
def active(request, pattern):
    """
    Simple tag let us define a regex for the active navigation tab
    """
    if re.search(pattern, request.path):
        return "active"
    return ""
