from django import template
from datetime import datetime
from django.utils import simplejson

register = template.Library()

@register.simple_tag(takes_context=True)
def get_list_class(context, list):
    """
    Returns the class to use for the passed in list.  We just build something up
    from the object type for the list.
    """
    css = "list_%s_%s" % (list.model._meta.app_label, list.model._meta.module_name)
    return css

@register.simple_tag(takes_context=True)
def get_value_from_view(context, field):
    """
    Responsible for deriving the displayed value for the passed in 'field'.

    This first checks for a particular method on the ListView, then looks for a method
    on the object, then finally treats it as an attribute.
    """
    view = context['view']
    value = view.lookup_field_value(context, None, field)
    if type(value) == datetime:
        return value.strftime("%b %d, %Y %H:%M")

    return value

@register.simple_tag(takes_context=True)
def get_value(context, obj, field):
    """
    Responsible for deriving the displayed value for the passed in 'field'.

    This first checks for a particular method on the ListView, then looks for a method
    on the object, then finally treats it as an attribute.
    """
    view = context['view']
    value = view.lookup_field_value(context, obj, field)
    if type(value) == datetime:
        return value.strftime("%b %d, %Y %H:%M")

    return value

@register.simple_tag(takes_context=True)
def get_class(context, field, obj=None):
    """
    Looks up the class for this field
    """
    view = context['view']
    return view.lookup_field_class(field, obj)

@register.simple_tag(takes_context=True)
def get_label(context, field, obj=None):
    """
    Responsible for figuring out the right label for the passed in field.

    The order of precedence is:
       1) if the view has a field_config and a label specified there, use that label
       2) check for a form in the view, if it contains that field, use it's value
    """
    view = context['view']
    return view.lookup_field_label(context, field, obj)

@register.simple_tag(takes_context=True)
def get_field_link(context, field, obj=None):
    """
    Determine what the field link should be for the given field, object pair
    """
    view = context['view']
    return view.lookup_field_link(context, field, obj)

@register.simple_tag(takes_context=True)
def view_as_json(context):
    """
    Responsible for figuring out the right label for the passed in field.

    The order of precedence is:
       1) if the view has a field_config and a label specified there, use that label
       2) check for a form in the view, if it contains that field, use it's value
    """
    view = context['view']
    return simplejson.dumps(view.as_json(context))

@register.filter
def field(form, field):
    for form_field in form:
        if form_field.name == field:
            return form_field

    return None

@register.filter
def map(string, object):
    return string % object.__dict__

@register.filter
def field_help(view, field):
    """
    Returns the field help for the passed in field
    """
    return view.lookup_field_help(field)

@register.filter
def field_orderable(view, field):
    """
    Returns whether the passed in field is orderable
    """
    return view.lookup_field_orderable(field)

#
# Woot woot, simple pdb debugging. {% pdb %}
#
class PDBNode(template.Node):
    def render(self, context):
        import pdb; pdb.set_trace()

@register.tag
def pdb(parser, token):
    return PDBNode()


