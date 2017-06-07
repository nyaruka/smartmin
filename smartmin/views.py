from __future__ import unicode_literals

import django.forms.models as model_forms
import json
import operator
import six

from django import forms
from django.conf import settings
from django.conf.urls import url
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.utils.encoding import force_text
from django.utils.http import urlquote
from django.utils.translation import ugettext_lazy as _
from django.views.generic.edit import ModelFormMixin, UpdateView, CreateView, ProcessFormView, FormView
from django.views.generic.base import TemplateView
from django.views.generic import DetailView, ListView
from functools import reduce
from smartmin.csv_imports.models import ImportTask
from smartmin.mixins import NonAtomicMixin
from . import widgets


def smart_url(url, obj=None):
    """
    URLs that start with @ are reversed, using the passed in arguments.

    Otherwise a straight % substitution is applied.
    """
    if url.find("@") >= 0:
        (args, value) = url.split('@')

        if args:
            val = getattr(obj, args, None)
            return reverse(value, args=[val])
        else:
            return reverse(value)
    else:
        if obj is None:
            return url
        else:
            return url % obj.id


class SmartView(object):
    fields = None
    exclude = None
    field_config = {}
    title = None
    refresh = 0
    template_name = None
    pjax = None

    # set by our CRUDL
    url_name = None

    # if we are part of a CRUDL, we keep a reference to it here, set by CRUDL
    crudl = None

    def __init__(self, *args):
        """
        There are a few variables we want to mantain in the instance, not the
        class.
        """
        self.extra_context = {}
        super(SmartView, self).__init__()

    def derive_title(self):
        """
        Returns the title used on this page.
        """
        return self.title

    @classmethod
    def derive_url_pattern(cls, path, action):
        """
        Returns the URL pattern for this view.
        """
        return r'^%s/%s/$' % (path, action)

    def has_permission(self, request, *args, **kwargs):
        """
        Figures out if the current user has permissions for this view.
        """
        self.kwargs = kwargs
        self.args = args
        self.request = request

        if not getattr(self, 'permission', None):
            return True
        else:
            return request.user.has_perm(self.permission)

    def dispatch(self, request, *args, **kwargs):
        """
        Overloaded to check permissions if appropriate
        """
        def wrapper(request, *args, **kwargs):
            if not self.has_permission(request, *args, **kwargs):
                path = urlquote(request.get_full_path())
                login_url = kwargs.pop('login_url', settings.LOGIN_URL)
                redirect_field_name = kwargs.pop('redirect_field_name', REDIRECT_FIELD_NAME)
                return HttpResponseRedirect("%s?%s=%s" % (login_url, redirect_field_name, path))
            else:
                response = self.pre_process(request, *args, **kwargs)
                if not response:
                    return super(SmartView, self).dispatch(request, *args, **kwargs)
                else:
                    return response

        return wrapper(request, *args, **kwargs)

    def pre_process(self, request, *args, **kwargs):
        """
        Gives the view an opportunity to intercept this response and return a different
        response instead.  This can be used to check some precondition for example and to
        redirect the user somewhere else if they are not met.

        Views which wish to use this should return a Response object.
        """
        return None

    def lookup_obj_attribute(self, obj, field):
        """
        Looks for a field's value from the passed in obj.  Note that this will strip
        leading attributes to deal with subelements if possible
        """
        curr_field = field.encode('ascii', 'ignore').decode("utf-8")
        rest = None

        if field.find('.') >= 0:
            curr_field = field.split('.')[0]
            rest = '.'.join(field.split('.')[1:])

        # next up is the object itself
        obj_field = getattr(obj, curr_field, None)

        # if it is callable, do so
        if obj_field and getattr(obj_field, '__call__', None):
            obj_field = obj_field()

        if obj_field and rest:
            return self.lookup_obj_attribute(obj_field, rest)
        else:
            return obj_field

    def lookup_field_value(self, context, obj, field):
        """
        Looks up the field value for the passed in object and field name.

        Note that this method is actually called from a template, but this provides a hook
        for subclasses to modify behavior if they wish to do so.

        This may be used for example to change the display value of a variable depending on
        other variables within our context.
        """
        curr_field = field.encode('ascii', 'ignore').decode("utf-8")

        # if this isn't a subfield, check the view to see if it has a get_ method
        if field.find('.') == -1:
            # view supercedes all, does it have a 'get_' method for this obj
            view_method = getattr(self, 'get_%s' % curr_field, None)
            if view_method:
                return view_method(obj)

        return self.lookup_obj_attribute(obj, field)

    def lookup_field_label(self, context, field, default=None):
        """
        Figures out what the field label should be for the passed in field name.

        Our heuristic is as follows:
            1) we check to see if our field_config has a label specified
            2) if not, then we derive a field value from the field name
        """
        # if this is a subfield, strip off everything but the last field name
        if field.find('.') >= 0:
            return self.lookup_field_label(context, field.split('.')[-1], default)

        label = None

        # is there a label specified for this field
        if field in self.field_config and 'label' in self.field_config[field]:
            label = self.field_config[field]['label']

        # if we were given a default, use that
        elif default:
            label = default

        # check our model
        else:
            for model_field in self.model._meta.fields:
                if model_field.name == field:
                    return model_field.verbose_name.title()

        # otherwise, derive it from our field name
        if label is None:
            label = self.derive_field_label(field)

        return label

    def lookup_field_help(self, field, default=None):
        """
        Looks up the help text for the passed in field.
        """
        help = None

        # is there a label specified for this field
        if field in self.field_config and 'help' in self.field_config[field]:
            help = self.field_config[field]['help']

        # if we were given a default, use that
        elif default:
            help = default

        # try to see if there is a description on our model
        elif hasattr(self, 'model'):
            for model_field in self.model._meta.fields:
                if model_field.name == field:
                    help = model_field.help_text
                    break

        return help

    def lookup_field_class(self, field, obj=None, default=None):
        """
        Looks up any additional class we should include when rendering this field
        """
        css = ""

        # is there a class specified for this field
        if field in self.field_config and 'class' in self.field_config[field]:
            css = self.field_config[field]['class']

        # if we were given a default, use that
        elif default:
            css = default

        return css

    def derive_field_label(self, field, obj=None):
        """
        Derives a field label for the passed in field name.
        """
        # replace _'s with ' '
        label = field.replace('_', ' ').title()
        return label

    def derive_field_config(self):
        """
        Derives the field config for this instance.  By default we just use
        self.field_config
        """
        return self.field_config

    def get_template_names(self):
        """
        Returns the name of the template to use to render this request.

        Smartmin provides default templates as fallbacks, so appends it's own templates names to the end
        of whatever list is built by the generic views.

        Subclasses can override this by setting a 'template_name' variable on the class.
        """
        templates = []
        if getattr(self, 'template_name', None):
            templates.append(self.template_name)

        if getattr(self, 'default_template', None):
            templates.append(self.default_template)
        else:
            templates = super(SmartView, self).get_template_names()

        return templates

    def derive_fields(self):
        """
        Default implementation
        """
        fields = []
        if self.fields:
            fields.append(self.fields)

        return fields

    def derive_exclude(self):
        """
        Returns which fields we should exclude
        """
        exclude = []
        if self.exclude:
            exclude += self.exclude

        return exclude

    def derive_refresh(self):
        """
        Returns how many milliseconds before we should refresh
        """
        return self.refresh

    def get_context_data(self, **kwargs):
        """
        We supplement the normal context data by adding our fields and labels.
        """
        context = super(SmartView, self).get_context_data(**kwargs)

        # derive our field config
        self.field_config = self.derive_field_config()

        # add our fields
        self.fields = self.derive_fields()

        # build up our current parameter string, EXCLUSIVE of our page.  These
        # are used to build pagination URLs
        url_params = "?"
        order_params = ""
        for key in self.request.GET.keys():
            if key != 'page' and key != 'pjax' and key[0] != '_':
                for value in self.request.GET.getlist(key):
                    url_params += "%s=%s&" % (key, urlquote(value))
            elif key == '_order':
                order_params = "&".join(["%s=%s" % (key, _) for _ in self.request.GET.getlist(key)])

        context['url_params'] = url_params
        context['order_params'] = order_params + "&"
        context['pjax'] = self.pjax

        # set our blocks
        context['blocks'] = dict()

        # stuff it all in our context
        context['fields'] = self.fields
        context['view'] = self
        context['field_config'] = self.field_config

        context['title'] = self.derive_title()

        # and any extra context the user specified
        context.update(self.extra_context)

        # by default, our base is 'base.html', but we might be pjax
        base_template = "base.html"
        if 'pjax' in self.request.GET or 'pjax' in self.request.POST:
            base_template = "smartmin/pjax.html"

        if 'HTTP_X_PJAX' in self.request.META:
            base_template = "smartmin/pjax.html"

        context['base_template'] = base_template

        # set our refresh if we have one
        refresh = self.derive_refresh()
        if refresh:
            context['refresh'] = refresh

        return context

    def as_json(self, context):
        """
        Responsible for turning our context into an dict that can then be serialized into an
        JSON response.
        """
        return context

    def render_to_response(self, context, **response_kwargs):
        """
        Overloaded to deal with _format arguments.
        """
        # should we actually render in json?
        if '_format' in self.request.GET and self.request.GET['_format'] == 'json':
            return JsonResponse(self.as_json(context), safe=False)

        # otherwise, return normally
        else:
            return super(SmartView, self).render_to_response(context)


class SmartTemplateView(SmartView, TemplateView):
    pass


def derive_single_object_url_pattern(slug_url_kwarg, path, action):
    """
    Utility function called by class methods for single object views
    """
    if slug_url_kwarg:
        return r'^%s/%s/(?P<%s>[^/]+)/$' % (path, action, slug_url_kwarg)
    else:
        return r'^%s/%s/(?P<pk>\d+)/$' % (path, action)


class SmartSingleObjectView(SmartView):
    slug_field = None
    slug_url_kwarg = None

    def get_slug_field(self):
        """
        If `slug_field` isn't specified it defaults to `slug_url_kwarg`
        """
        return self.slug_field if self.slug_field else self.slug_url_kwarg


class SmartReadView(SmartSingleObjectView, DetailView):
    default_template = 'smartmin/read.html'
    edit_button = None

    field_config = {'modified_blurb': dict(label="Modified"),
                    'created_blurb': dict(label="Created")}

    @classmethod
    def derive_url_pattern(cls, path, action):
        return derive_single_object_url_pattern(cls.slug_url_kwarg, path, action)

    def derive_queryset(self):
        return super(SmartReadView, self).get_queryset()

    def get_queryset(self):
        self.queryset = self.derive_queryset()
        return self.queryset

    def derive_title(self):
        """
        By default we just return the string representation of our object
        """
        return str(self.object)

    def derive_fields(self):
        """
        Derives our fields.  We first default to using our 'fields' variable if available,
        otherwise we figure it out from our object.
        """
        if self.fields:
            return list(self.fields)

        else:
            fields = []
            for field in self.object._meta.fields:
                fields.append(field.name)

            # only exclude?  then remove those items there
            exclude = self.derive_exclude()

            # remove any excluded fields
            fields = [field for field in fields if field not in exclude]

            return fields

    def get_modified_blurb(self, obj):
        return "%s by %s" % (obj.modified_on.strftime("%B %d, %Y at %I:%M %p"), obj.modified_by)

    def get_created_blurb(self, obj):
        return "%s by %s" % (obj.created_on.strftime("%B %d, %Y at %I:%M %p"), obj.created_by)


class SmartDeleteView(SmartSingleObjectView, DetailView, ProcessFormView):
    default_template = 'smartmin/delete_confirm.html'
    name_field = 'name'
    cancel_url = None
    redirect_url = None

    @classmethod
    def derive_url_pattern(cls, path, action):
        return derive_single_object_url_pattern(cls.slug_url_kwarg, path, action)

    def get_cancel_url(self):
        if not self.cancel_url:
            raise ImproperlyConfigured("DeleteView must define a cancel_url")

        return smart_url(self.cancel_url, self.object)

    def pre_delete(self, obj):
        # auto populate modified_by if it is present
        if hasattr(obj, 'modified_by_id') and self.request.user.id >= 0:
            obj.modified_by = self.request.user

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.pre_delete(self.object)
        redirect_url = self.get_redirect_url()
        self.object.delete()

        return HttpResponseRedirect(redirect_url)

    def get_redirect_url(self, **kwargs):
        if not self.redirect_url:
            raise ImproperlyConfigured("DeleteView must define a redirect_url")

        return smart_url(self.redirect_url)

    def get_context_data(self, **kwargs):
        """ Add in the field to use for the name field """
        context = super(SmartDeleteView, self).get_context_data(**kwargs)
        context['name_field'] = self.name_field
        context['cancel_url'] = self.get_cancel_url()
        return context


class SmartListView(SmartView, ListView):
    default_template = 'smartmin/list.html'

    link_url = None
    link_fields = None
    add_button = None
    search_fields = None
    paginate_by = 25
    field_config = {'is_active': dict(label='')}
    default_order = None
    select_related = None

    @classmethod
    def derive_url_pattern(cls, path, action):
        if action == 'list':
            return r'^%s/$' % (path)
        else:
            return r'^%s/%s/$' % (path, action)

    def derive_search_fields(self):
        """
        Derives our search fields, by default just returning what was set
        """
        return self.search_fields

    def derive_title(self):
        """
        Derives our title from our list
        """
        title = super(SmartListView, self).derive_title()

        if not title:
            return force_text(self.model._meta.verbose_name_plural).title()
        else:
            return title

    def derive_link_fields(self, context):
        """
        Used to derive which fields should be linked.  This should return a set() containing
        the names of those fields which should be linkable.
        """
        if self.link_fields is not None:
            return self.link_fields

        else:
            link_fields = set()
            if self.fields:
                for field in self.fields:
                    if field != 'is_active':
                        link_fields.add(field)
                        break

        return link_fields

    def lookup_field_link(self, context, field, obj):
        """
        By default we just return /view/{{ id }}/ for the current object.
        """
        return smart_url(self.link_url, obj)

    def lookup_field_orderable(self, field):
        """
        Returns whether the passed in field is sortable or not, by default all 'raw' fields, that
        is fields that are part of the model are sortable.
        """
        try:
            self.model._meta.get_field_by_name(field)
            return True
        except:
            # that field doesn't exist, so not sortable
            return False

    def get_context_data(self, **kwargs):
        """
        Add in what fields are linkable
        """
        context = super(SmartListView, self).get_context_data(**kwargs)

        # our linkable fields
        self.link_fields = self.derive_link_fields(context)

        # stuff it all in our context
        context['link_fields'] = self.link_fields

        # our search term if any
        if 'search' in self.request.GET:
            context['search'] = self.request.GET['search']

        # our ordering field if any
        order = self.derive_ordering()
        if order:
            if order[0] == '-':
                context['order'] = order[1:]
                context['order_asc'] = False
            else:
                context['order'] = order
                context['order_asc'] = True

        return context

    def derive_select_related(self):
        return self.select_related

    def derive_queryset(self, **kwargs):
        """
        Derives our queryset.
        """
        # get our parent queryset
        queryset = super(SmartListView, self).get_queryset(**kwargs)

        # apply any filtering
        search_fields = self.derive_search_fields()
        search_query = self.request.GET.get('search')
        if search_fields and search_query:
            term_queries = []
            for term in search_query.split(' '):
                field_queries = []
                for field in search_fields:
                    field_queries.append(Q(**{field: term}))
                term_queries.append(reduce(operator.or_, field_queries))

            queryset = queryset.filter(reduce(operator.and_, term_queries))

        # add any select related
        related = self.derive_select_related()
        if related:
            queryset = queryset.select_related(*related)

        # return our queryset
        return queryset

    def get_queryset(self, **kwargs):
        """
        Gets our queryset.  This takes care of filtering if there are any
        fields to filter by.
        """
        queryset = self.derive_queryset(**kwargs)

        return self.order_queryset(queryset)

    def derive_ordering(self):
        """
        Returns what field should be used for ordering (using a prepended '-' to indicate descending sort).

        If the default order of the queryset should be used, returns None
        """
        if '_order' in self.request.GET:
            return self.request.GET['_order']
        elif self.default_order:
            return self.default_order
        else:
            return None

    def order_queryset(self, queryset):
        """
        Orders the passed in queryset, returning a new queryset in response.  By default uses the _order query
        parameter.
        """
        order = self.derive_ordering()

        # if we get our order from the request
        # make sure it is a valid field in the list
        if '_order' in self.request.GET:
            if order.lstrip('-') not in self.derive_fields():
                order = None

        if order:
            # if our order is a single string, convert to a simple list
            if isinstance(order, six.string_types):
                order = (order,)

            queryset = queryset.order_by(*order)

        return queryset

    def derive_fields(self):
        """
        Derives our fields.
        """
        if self.fields:
            return self.fields

        else:
            fields = []
            for field in self.object_list.model._meta.fields:
                if field.name != 'id':
                    fields.append(field.name)
            return fields

    def get_is_active(self, obj):
        """
        Default implementation of get_is_active which returns a simple div so as to
        render a green dot for active items and nothing for inactive ones.

        Users of SmartModel will get this rendering for free.
        """
        if obj.is_active:
            return '<div class="active_icon"></div>'
        else:
            return ''

    def render_to_response(self, context, **response_kwargs):
        """
        Overloaded to deal with _format arguments.
        """
        # is this a select2 format response?
        if self.request.GET.get('_format', 'html') == 'select2':

            results = []
            for obj in context['object_list']:
                result = None
                if hasattr(obj, 'as_select2'):
                    result = obj.as_select2()

                if not result:
                    result = dict(id=obj.pk, text="%s" % obj)

                results.append(result)

            json_data = dict(results=results, err='nil', more=context['page_obj'].has_next())
            return JsonResponse(json_data)
        # otherwise, return normally
        else:
            return super(SmartListView, self).render_to_response(context)


class SmartCsvView(SmartListView):

    def derive_filename(self):
        filename = getattr(self, 'filename', None)
        if not filename:
            filename = "%s.csv" % self.model._meta.verbose_name.lower()
        return filename

    def render_to_response(self, context, **response_kwargs):
        import csv

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename=%s' % self.derive_filename()

        writer = csv.writer(response, quoting=csv.QUOTE_ALL)

        fields = self.derive_fields()

        # build up our header row
        header = []
        for field in fields:
            header.append(six.text_type(self.lookup_field_label(dict(), field)))
        writer.writerow([s.encode("utf-8") for s in header])

        # then our actual values
        for obj in self.object_list:
            row = []
            for field in fields:
                row.append(six.text_type(self.lookup_field_value(dict(), obj, field)))
            writer.writerow([s.encode("utf-8") for s in row])

        return response


class SmartXlsView(SmartListView):

    def derive_filename(self):
        filename = getattr(self, 'filename', None)
        if not filename:
            filename = "%s.xls" % self.model._meta.verbose_name.lower()
        return filename

    def render_to_response(self, context, **response_kwargs):

        from xlwt import Workbook
        book = Workbook()
        sheet1 = book.add_sheet(self.derive_title())
        fields = self.derive_fields()

        # build up our header row
        for col in range(len(fields)):
            field = fields[col]
            sheet1.write(0, col, six.text_type(self.lookup_field_label(dict(), field)))

        # then our actual values
        for row in range(len(self.object_list)):
            obj = self.object_list[row]
            for col in range(len(fields)):
                field = fields[col]
                value = six.text_type(self.lookup_field_value(dict(), obj, field))
                # skip the header
                sheet1.write(row + 1, col, value)

        # Create the HttpResponse object with the appropriate header.
        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=%s' % self.derive_filename()
        book.save(response)
        return response


class SmartFormMixin(object):
    readonly = ()
    field_config = {'modified_blurb': dict(label="Modified"),
                    'created_blurb': dict(label="Created")}
    success_message = None
    submit_button_name = _("Submit")

    def derive_title(self):
        """
        Derives our title from our object
        """
        if not self.title:
            return _("Form")
        else:
            return self.title

    def derive_success_message(self):
        """
        Returns a message to display when this form is successfully saved
        """
        return self.success_message

    def get_form(self):
        """
        Returns an instance of the form to be used in this view.
        """
        self.form = super(SmartFormMixin, self).get_form()

        fields = list(self.derive_fields())

        # apply our field filtering on our form class
        exclude = self.derive_exclude()
        exclude += self.derive_readonly()

        # remove any excluded fields
        for field in exclude:
            if field in self.form.fields:
                del self.form.fields[field]

        if fields is not None:
            # filter out our form fields
            remove = [name for name in self.form.fields.keys() if name not in fields]
            for name in remove:
                del self.form.fields[name]

        # stuff in our referer as the default location for where to return
        location = forms.CharField(widget=forms.widgets.HiddenInput(), required=False)

        if ('HTTP_REFERER' in self.request.META):
            location.initial = self.request.META['HTTP_REFERER']

        # add the location to our form fields
        self.form.fields['loc'] = location

        if fields:
            fields.append('loc')

        # provides a hook to programmatically customize fields before rendering
        for (name, field) in self.form.fields.items():
            field = self.customize_form_field(name, field)
            self.form.fields[name] = field

        return self.form

    def customize_form_field(self, name, field):
        """
        Allows views to customize their form fields.  By default, Smartmin replaces the plain textbox
        date input with it's own DatePicker implementation.
        """
        if isinstance(field, forms.fields.DateField) and isinstance(field.widget, forms.widgets.DateInput):
            field.widget = widgets.DatePickerWidget()
            field.input_formats = [field.widget.input_format[1]] + list(field.input_formats)

        if isinstance(field, forms.fields.ImageField) and isinstance(field.widget, forms.widgets.ClearableFileInput):
            field.widget = widgets.ImageThumbnailWidget()

        return field

    def lookup_field_label(self, context, field, default=None):
        """
        Figures out what the field label should be for the passed in field name.

        We overload this so as to use our form to see if there is label set there.  If so
        then we'll pass that as the default instead of having our parent derive
        the field from the name.
        """
        default = None

        for form_field in self.form:
            if form_field.name == field:
                default = form_field.label
                break

        return super(SmartFormMixin, self).lookup_field_label(context, field, default=default)

    def lookup_field_help(self, field, default=None):
        """
        Looks up the help text for the passed in field.

        This is overloaded so that we can check whether our form has help text set
        explicitely.  If so, we will pass this as the default to our parent function.
        """
        default = None

        for form_field in self.form:
            if form_field.name == field:
                default = form_field.help_text
                break

        return super(SmartFormMixin, self).lookup_field_help(field, default=default)

    def derive_readonly(self):
        """
        Figures out what fields should be readonly.  We iterate our field_config to find all
        that have a readonly of true
        """
        readonly = list(self.readonly)
        for key, value in self.field_config.items():
            if 'readonly' in value and value['readonly']:
                readonly.append(key)

        return readonly

    def derive_fields(self):
        """
        Derives our fields.
        """
        if self.fields is not None:
            fields = list(self.fields)
        else:
            form = self.form
            fields = []
            for field in form:
                fields.append(field.name)

            # this is slightly confusing but we add in readonly fields here because they will still
            # need to be displayed
            readonly = self.derive_readonly()
            if readonly:
                fields += readonly

        # remove any excluded fields
        for exclude in self.derive_exclude():
            if exclude in fields:
                fields.remove(exclude)

        return fields

    def get_form_class(self):
        """
        Returns the form class to use in this view
        """
        if self.form_class:
            form_class = self.form_class

        else:
            if self.model is not None:
                # If a model has been explicitly provided, use it
                model = self.model
            elif hasattr(self, 'object') and self.object is not None:
                # If this view is operating on a single object, use
                # the class of that object
                model = self.object.__class__
            else:
                # Try to get a queryset and extract the model class
                # from that
                model = self.get_queryset().model

            # run time parameters when building our form
            factory_kwargs = self.get_factory_kwargs()
            form_class = model_forms.modelform_factory(model, **factory_kwargs)

        return form_class

    def get_factory_kwargs(self):
        """
        Let's us specify any extra parameters we might want to call for our form factory.

        These can include: 'form', 'fields', 'exclude' or 'formfield_callback'
        """
        params = dict()

        exclude = self.derive_exclude()
        exclude += self.derive_readonly()

        if self.fields:
            fields = list(self.fields)
            for ex in exclude:
                if ex in fields:
                    fields.remove(ex)

            params['fields'] = fields

        if exclude:
            params['exclude'] = exclude

        return params

    def get_success_url(self):
        """
        By default we use the referer that was stuffed in our
        form when it was created
        """
        if self.success_url:
            # if our smart url references an object, pass that in
            if self.success_url.find('@') > 0:
                return smart_url(self.success_url, self.object)
            else:
                return smart_url(self.success_url, None)

        elif 'loc' in self.form.cleaned_data:
            return self.form.cleaned_data['loc']

        raise ImproperlyConfigured("No redirect location found, override get_success_url to not use redirect urls")

    def derive_initial(self):
        """
        Returns what initial dict should be passed to our form. By default this is empty.
        """
        return dict()

    def get_form_kwargs(self):
        """
        We override this, using only those fields specified if they are specified.

        Otherwise we include all fields in a standard ModelForm.
        """
        kwargs = super(SmartFormMixin, self).get_form_kwargs()
        kwargs['initial'] = self.derive_initial()
        return kwargs

    def derive_submit_button_name(self):
        """
        Returns the name for our button
        """
        return self.submit_button_name

    def get_context_data(self, **kwargs):
        context = super(SmartFormMixin, self).get_context_data(**kwargs)
        context['submit_button_name'] = self.derive_submit_button_name()
        return context


class SmartFormView(SmartFormMixin, SmartView, FormView):
    default_template = 'smartmin/form.html'

    def form_valid(self, form):
        # plug in our success message
        messages.success(self.request, self.derive_success_message())
        return super(SmartFormView, self).form_valid(form)


class SmartModelFormView(SmartFormMixin, SmartSingleObjectView, ModelFormMixin):
    javascript_submit = None

    field_config = {'modified_blurb': dict(label="Modified"), 'created_blurb': dict(label="Created")}

    def derive_title(self):
        """
        Derives our title from our object
        """
        if not self.title:
            return _("Edit %s") % force_text(self.model._meta.verbose_name).title()
        else:
            return self.title

    def pre_save(self, obj):
        """
        Called before an object is saved away
        """
        return obj

    def save(self, obj):
        """
        Actually does the saving of this object, this is when the object is committed
        """
        self.object.save()
        self.save_m2m()

    def form_valid(self, form):
        self.object = form.save(commit=False)

        try:
            self.object = self.pre_save(self.object)
            self.save(self.object)
            self.object = self.post_save(self.object)

            messages.success(self.request, self.derive_success_message())
            if 'HTTP_X_FORMAX' not in self.request.META:
                return HttpResponseRedirect(self.get_success_url())
            else:
                response = self.render_to_response(self.get_context_data(form=form))
                response['REDIRECT'] = self.get_success_url()
                return response

        except IntegrityError as e:
            message = str(e).capitalize()
            errors = self.form._errors.setdefault(forms.forms.NON_FIELD_ERRORS, forms.utils.ErrorList())
            errors.append(message)
            return self.render_to_response(self.get_context_data(form=form))

    def save_m2m(self):
        """
        By default saves the form's m2m, can be overridden if a more complicated m2m model exists
        """
        self.form.save_m2m()

    def post_save(self, obj):
        """
        Called after an object is successfully saved
        """
        return obj

    def get_context_data(self, **kwargs):
        context = super(SmartModelFormView, self).get_context_data(**kwargs)
        context['javascript_submit'] = self.javascript_submit
        return context


class SmartUpdateView(SmartModelFormView, UpdateView):
    default_template = 'smartmin/update.html'
    exclude = ('created_by', 'modified_by')
    submit_button_name = _("Save Changes")

    # allows you to specify the name of URL to use for a remove link that will automatically be shown
    delete_url = None

    @classmethod
    def derive_url_pattern(cls, path, action):
        return derive_single_object_url_pattern(cls.slug_url_kwarg, path, action)

    def derive_queryset(self):
        return super(SmartUpdateView, self).get_queryset()

    def get_queryset(self):
        self.queryset = self.derive_queryset()
        return self.queryset

    def derive_success_message(self):
        # First check whether a default message has been set
        if self.success_message is None:
            return "Your %s has been updated." % self.model._meta.verbose_name
        else:
            return self.success_message

    def pre_save(self, obj):
        # auto populate modified_by if it is present
        if hasattr(obj, 'modified_by_id') and self.request.user.id >= 0:
            obj.modified_by = self.request.user

        return obj

    def get_context_data(self, **kwargs):
        context = super(SmartUpdateView, self).get_context_data(**kwargs)

        if self.delete_url:
            context['delete_url'] = smart_url(self.delete_url, self.object)

        return context

    def get_modified_blurb(self, obj):
        return "%s by %s" % (obj.modified_on.strftime("%B %d, %Y at %I:%M %p"), obj.modified_by)

    def get_created_blurb(self, obj):
        return "%s by %s" % (obj.created_on.strftime("%B %d, %Y at %I:%M %p"), obj.created_by)


class SmartModelActionView(SmartFormMixin, SmartSingleObjectView, DetailView, ProcessFormView):

    @classmethod
    def derive_url_pattern(cls, path, action):
        return derive_single_object_url_pattern(cls.slug_url_kwarg, path, action)

    def execute_action(self):
        """
        Subclasses should do their work here. They can throw a ValidationError to return
        control back to the Form input with said error. If no error is thrown page will
        be redirected to success_url
        """
        pass

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(SmartModelActionView, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            self.execute_action()

        except forms.ValidationError as e:
            # turns out we aren't valid after all, stuff our error into our form
            self.form.add_error(None, e)
            return self.form_invalid(form)

        # all went well, stuff our success message in and return
        messages.success(self.request, self.derive_success_message())
        return super(SmartModelActionView, self).form_valid(form)


class SmartMultiFormView(SmartView, TemplateView):
    default_template = 'smartmin/multi_form.html'
    forms = {}

    # allows you to specify the name of URL to use for a remove link that will automatically be shown
    delete_url = None

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        page_forms = []
        for prefix, form in self.forms.items():
            f = form(prefix=prefix)
            page_forms.append(f)

        context['forms'] = page_forms

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        # process our forms
        page_forms = []
        valid = True
        for prefix, form in self.forms.items():
            f = form(request.POST, prefix=prefix)
            valid = valid and f.is_valid()
            page_forms.append(f)

        if not valid:
            context['forms'] = page_forms
            return self.render_to_response(context)
        else:
            # redirect to success page
            pass

    def get_context_data(self, **kwargs):
        context = super(SmartMultiFormView, self).get_context_data(**kwargs)

        if self.delete_url:
            context['delete_url'] = smart_url(self.delete_url, self.object)

        return context


class SmartCreateView(SmartModelFormView, CreateView):
    default_template = 'smartmin/create.html'
    exclude = ('created_by', 'modified_by', 'is_active')
    submit_button_name = _("Create")

    def has_object_permission(self, getter_name):
        # create views don't have an object, so this is always False
        return False

    def pre_save(self, obj):
        # auto populate created_by if it is present
        if hasattr(obj, 'created_by_id') and self.request.user.id >= 0:
            obj.created_by = self.request.user

        # auto populate modified_by if it is present
        if hasattr(obj, 'modified_by_id') and self.request.user.id >= 0:
            obj.modified_by = self.request.user

        return obj

    def derive_success_message(self):
        # First check whether a default message has been set
        if self.success_message is None:
            return _("Your new %s has been created.") % self.model._meta.verbose_name
        else:
            return self.success_message

    def derive_title(self):
        """
        Derives our title from our object
        """
        if not self.title:
            return _("Create %s") % force_text(self.model._meta.verbose_name).title()
        else:
            return self.title


class SmartCSVImportView(NonAtomicMixin, SmartCreateView):
    success_url = 'id@csv_imports.importtask_read'

    fields = ('csv_file',)

    def derive_title(self):
        return _("Import %s") % self.crudl.model._meta.verbose_name_plural.title()

    def pre_save(self, obj):
        obj = super(SmartCSVImportView, self).pre_save(obj)
        obj.model_class = "%s.%s" % (self.crudl.model.__module__, self.crudl.model.__name__)
        return obj

    def post_save(self, task):
        task = super(SmartCSVImportView, self).post_save(task)

        task.import_params = json.dumps(self.form.data)

        # kick off our CSV import
        task.start()

        return task


class SmartCRUDL(object):
    actions = ('create', 'read', 'update', 'delete', 'list')
    model_name = None
    app_name = None
    module_name = None
    path = None

    permissions = True

    def __init__(self, model=None, path=None, actions=None):
        # set our model if passed in
        if model:
            self.model = model

        # derive our model name
        if not self.model_name:
            self.model_name = self.model._meta.object_name

        # derive our app name
        if not self.app_name:
            self.app_name = self.model._meta.app_label

        # derive our path from our class name
        if not path and not self.path:
            self.path = self.model_name.lower()

        # derive our module name from our class's module
        if not self.module_name:
            parts = self.__class__.__module__.split(".")
            self.module_name = parts[-2]

            # deal with special case of views subdirectories, we need to go up one more to find the real module
            if self.module_name == 'views' and len(parts) >= 3:
                self.module_name = parts[-3]

        # set our actions if set
        if actions:
            self.actions = actions

    def permission_for_action(self, action):
        """
        Returns the permission to use for the passed in action
        """
        return "%s.%s_%s" % (self.app_name.lower(), self.model_name.lower(), action)

    def template_for_action(self, action):
        """
        Returns the template to use for the passed in action
        """
        return "%s/%s_%s.html" % (self.module_name.lower(), self.model_name.lower(), action)

    def url_name_for_action(self, action):
        """
        Returns the reverse name for this action
        """
        return "%s.%s_%s" % (self.module_name.lower(), self.model_name.lower(), action)

    def view_for_action(self, action):
        """
        Returns the appropriate view class for the passed in action
        """
        # this turns replace_foo into ReplaceFoo and read into Read
        class_name = "".join([word.capitalize() for word in action.split("_")])
        view = None

        # see if we have a custom class defined for this action
        if hasattr(self, class_name):
            # return that one
            view = getattr(self, class_name)

            # no model set?  set it ourselves
            if not getattr(view, 'model', None):
                view.model = self.model

            # no permission and we are supposed to set them, do so
            if not hasattr(view, 'permission') and self.permissions:
                view.permission = self.permission_for_action(action)

            # set our link URL based on read and update
            if not getattr(view, 'link_url', None):
                if 'read' in self.actions:
                    view.link_url = 'id@%s' % self.url_name_for_action('read')
                elif 'update' in self.actions:
                    view.link_url = 'id@%s' % self.url_name_for_action('update')

            # if we can't infer a link URL then view class must override lookup_field_link
            if not getattr(view, 'link_url', None) and 'lookup_field_link' not in view.__dict__:
                view.link_fields = ()

            # set add_button based on existence of Create view if add_button not explicitly set
            if action == 'list' and getattr(view, 'add_button', None) is None:
                view.add_button = 'create' in self.actions

            # set edit_button based on existence of Update view if edit_button not explicitly set
            if action == 'read' and getattr(view, 'edit_button', None) is None:
                view.edit_button = 'update' in self.actions

            # if update or create, set success url if not set
            if not getattr(view, 'success_url', None) and (action == 'update' or action == 'create'):
                view.success_url = '@%s' % self.url_name_for_action('list')

        # otherwise, use our defaults
        else:
            options = dict(model=self.model)

            # if this is an update or create, and we have a list view, then set the default to that
            if action == 'update' or action == 'create' and 'list' in self.actions:
                options['success_url'] = '@%s' % self.url_name_for_action('list')

            # set permissions if appropriate
            if self.permissions:
                options['permission'] = self.permission_for_action(action)

            if action == 'create':
                view = type(str("%sCreateView" % self.model_name), (SmartCreateView,), options)

            elif action == 'read':
                if 'update' in self.actions:
                    options['edit_button'] = True

                view = type(str("%sReadView" % self.model_name), (SmartReadView,), options)

            elif action == 'update':
                if 'delete' in self.actions:
                    options['delete_url'] = 'id@%s' % self.url_name_for_action('delete')

                view = type(str("%sUpdateView" % self.model_name), (SmartUpdateView,), options)

            elif action == 'delete':
                if 'list' in self.actions:
                    options['cancel_url'] = '@%s' % self.url_name_for_action('list')
                    options['redirect_url'] = '@%s' % self.url_name_for_action('list')

                elif 'update' in self.actions:
                    options['cancel_url'] = '@%s' % self.url_name_for_action('update')

                view = type(str("%sDeleteView" % self.model_name), (SmartDeleteView,), options)

            elif action == 'list':
                if 'read' in self.actions:
                    options['link_url'] = 'id@%s' % self.url_name_for_action('read')
                elif 'update' in self.actions:
                    options['link_url'] = 'id@%s' % self.url_name_for_action('update')
                else:
                    options['link_fields'] = ()

                if 'create' in self.actions:
                    options['add_button'] = True

                view = type(str("%sListView" % self.model_name), (SmartListView,), options)

            elif action == 'csv_import':
                options['model'] = ImportTask
                view = type(str("%sCSVImportView" % self.model_name), (SmartCSVImportView,), options)

        if not view:
            # couldn't find a view?  blow up
            raise Exception("No view found for action: %s" % action)

        # set the url name for this view
        view.url_name = self.url_name_for_action(action)

        # no template set for it?  set one based on our action and app name
        if not getattr(view, 'template_name', None):
            view.template_name = self.template_for_action(action)

        view.crudl = self

        return view

    def pattern_for_view(self, view, action):
        """
        Returns the URL pattern for the passed in action.
        """
        # if this view knows how to define a URL pattern, call that
        if getattr(view, 'derive_url_pattern', None):
            return view.derive_url_pattern(self.path, action)

        # otherwise take our best guess
        else:
            return r'^%s/%s/$' % (self.path, action)

    def as_urlpatterns(self):
        """
        Creates the appropriate URLs for this object.
        """
        urls = []

        # for each of our actions
        for action in self.actions:
            view_class = self.view_for_action(action)
            view_pattern = self.pattern_for_view(view_class, action)
            name = self.url_name_for_action(action)
            urls.append(url(view_pattern, view_class.as_view(), name=name))

        return urls
