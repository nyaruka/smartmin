from django import template
from datetime import datetime
from django.utils import simplejson
from django.template import TemplateSyntaxError

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
    obj = None
    if 'object' in context:
        obj = context['object']

    value = view.lookup_field_value(context, obj, field)
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
    return view.lookup_field_class(field, obj, "field_" + field)

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
    Returns our view serialized as json
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
def map(string, args):
    return string % args.__dict__

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
        return ''

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

@register.simple_tag(takes_context=True)
def getblock(context, prefix, suffix=None):
    key = prefix
    if suffix:
        key += str(suffix)

    if not 'blocks' in context:
        raise TemplateSyntaxError("setblock/endblock can only be used with SmartView or it's subclasses")

    if key in context['blocks']:
        return context['blocks'][key]
    else:
        return ""

def setblock(parser, token):
    args = token.split_contents()
    if len(args) < 2:
        raise TemplateSyntaxError("setblock tag takes one argument, the name of the block got: [%s]" % ",".join(args))

    key = "".join(args[1:])
        
    nodelist = parser.parse(('endsetblock',))
    parser.delete_first_token()
    return SetBlockNode(key, nodelist)

class SetBlockNode(template.Node):
    def __init__(self, key, nodelist):
        self.key = key
        self.nodelist = nodelist
        
    def render(self, context):
        if not 'blocks' in context:
            raise TemplateSyntaxError("setblock/endblock can only be used with SmartView or it's subclasses")
        
        output = self.nodelist.render(context)
        context['blocks'][self.key] = output
        return ""

# register our tag
setblock = register.tag(setblock)

@register.inclusion_tag('smartmin/field.html', takes_context=True)
def render_field(context, field):
    form = context['form']
    view = context['view']

    readonly_fields = view.derive_readonly()

    # check that this field exists in our form, either as a real field or as a readonly one
    if not field in form.fields and not field in readonly_fields:
        raise TemplateSyntaxError("Error: No field '%s' found in form to render" % field)

    inclusion_context = dict(field = field,
                             form = context['form'],
                             view = context['view'],
                             blocks = context['blocks'])
    if 'object' in context:
        inclusion_context['object'] = context['object']

    return inclusion_context
    


