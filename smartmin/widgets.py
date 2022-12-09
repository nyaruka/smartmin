from django.forms import widgets
from django.utils.html import escape
from django.utils.safestring import mark_safe


class VisibleHiddenWidget(widgets.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        """
        Returns this Widget rendered as HTML, as a Unicode string.

        The 'value' given is not guaranteed to be valid input, so subclass
        implementations should program defensively.
        """
        html = ""
        html += "%s" % value
        html += '<input type="hidden" name="%s" value="%s">' % (escape(name), escape(value))
        return mark_safe(html)


class DatePickerWidget(widgets.DateInput):
    """
    Date input which uses Javascript date picker widget
    """

    input_format = ("MM d, yyyy", "%B %d, %Y")  # Javascript and Python format strings

    def __init__(self, *args, **kwargs):
        kwargs["attrs"] = {"data-provide": "datepicker", "data-date-format": self.input_format[0]}
        kwargs["format"] = self.input_format[1]

        super(DatePickerWidget, self).__init__(*args, **kwargs)

    class Media:
        js = ("js/bootstrap-datepicker.js",)
        css = {"all": ("css/bootstrap-datepicker3.css",)}


class ImageThumbnailWidget(widgets.ClearableFileInput):
    def __init__(self, thumb_width=75, thumb_height=75):
        self.width = thumb_width
        self.height = thumb_height
        super(ImageThumbnailWidget, self).__init__({})

    def render(self, name, value, attrs=None, renderer=None):
        thumb_html = "<table><tr>"
        if value and hasattr(value, "url"):
            try:
                from sorl.thumbnail import get_thumbnail

                value = get_thumbnail(value, f"{self.width}x{self.height}", crop="center", quality=99)
            except ImportError:
                pass

            thumb_html += '<td><img src="%s" width="%s" width="%s" /></td>' % (value.url, self.width, self.height)

        thumb_html += '<td><input type="checkbox" name="%s-clear" /> Clear' % name
        thumb_html += '<input type="file" name="%s" /></td>' % name
        thumb_html += "</tr></table>"

        return mark_safe(str('<div class="image-picker">%s</div>' % thumb_html))
