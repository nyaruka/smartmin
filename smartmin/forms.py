from django.forms import fields
from django.forms import widgets
from django.utils.safestring import mark_safe
from django.utils.html import escape, conditional_escape

class VisibleHiddenWidget(widgets.Widget):

    def render(self, name, value, attrs=None):
        """
        Returns this Widget rendered as HTML, as a Unicode string.

        The 'value' given is not guaranteed to be valid input, so subclass
        implementations should program defensively.
        """
        html = ''
        html += '%s' % value
        html += '<input type="hidden" name="%s" value="%s">' % (escape(name), escape(value))
        return mark_safe(html)


    
