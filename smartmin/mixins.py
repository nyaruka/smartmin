from __future__ import unicode_literals
"""
simple mixins that keep you from writing so much code
"""

from django.db import transaction
from django.utils.decorators import method_decorator


class PassRequestToFormMixin(object):
    """
    Mixin to include the request in the form kwargs
    """
    def get_form_kwargs(self):
        kwargs = super(PassRequestToFormMixin, self).get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


class NonAtomicMixin(object):
    """
    Mixin to configure a view to be handled without a transaction
    """
    @method_decorator(transaction.non_atomic_requests)
    def dispatch(self, request, *args, **kwargs):
        return super(NonAtomicMixin, self).dispatch(request, *args, **kwargs)
