from __future__ import unicode_literals

import six

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.test.testcases import TestCase
from django.utils.encoding import force_str
from six.moves.urllib.parse import urlparse


class SmartminTest(TestCase):

    def fetch_protected(self, url, user, post_data=None, failOnFormValidation=True):
        """
        Fetches the given url. Fails if it can be fetched without first logging in as given user
        """
        # make sure we are logged out before testing permissions
        self.client.logout()

        # can't load if we aren't logged in
        response = self.client.get(url)
        self.assertRedirect(response, reverse("users.user_login"), msg="'%s' loaded without being logged in first" % url)
        self.login(user)

        # but now we can!
        if not post_data:
            response = self.client.get(url)
            self.assertEquals(200, response.status_code)
        else:
            response = self.client.post(url, data=post_data)
            self.assertNotRedirect(response, reverse("users.user_login"), msg="Unexpected redirect to login")

            if failOnFormValidation:
                self.assertNoFormErrors(response, post_data)
                self.assertEquals(302, response.status_code)

        return response

    def assertLoginRedirect(self, response, msg=None):
        self.assertRedirect(response, settings.LOGIN_URL, msg)

    def assertRedirect(self, response, url, msg=None):
        self.assertEquals(302, response.status_code, msg=msg)
        segments = urlparse(response.get('Location', None))
        self.assertEquals(segments.path, url, msg=msg)

    def assertNotRedirect(self, response, url, msg=None):
        if response.status_code == 302:
            segments = urlparse(response.get('Location', None))
            self.assertNotEqual(segments.path, url, msg=msg)

    def create_user(self, username, group_names=()):
        # Create a user to run our CRUDL tests
        user = get_user_model().objects.create_user(username, "%s@nyaruka.com" % username)
        user.set_password(username)
        user.save()
        for group in group_names:
            user.groups.add(Group.objects.get(name=group))
        return user

    def login(self, user):
        self.assertTrue(self.client.login(username=user.username, password=user.username), "Couldn't login as %(user)s / %(user)s" % dict(user=user.username))

    def assertNoFormErrors(self, response, post_data=None):
        if response.status_code == 200 and 'form' in response.context:
            form = response.context['form']

            if not form.is_valid():
                errors = []
                for k, v in six.iteritems(form.errors):
                    errors.append("%s=%s" % (k, force_str(v)))
                self.fail("Create failed with form errors: %s, Posted: %s" % (",".join(errors), post_data))


class _CRUDLTest(SmartminTest):
    """
    Base class for standard CRUDL test cases
    """
    crudl = None
    user = None
    object = None

    def setUp(self):
        self.crudl = None
        self.user = None
        super(_CRUDLTest, self).setUp()

    def run(self, result=None):
        # only actually run sub classes of this
        if self.__class__ != _CRUDLTest:
            super(_CRUDLTest, self).run(result)

    def getCRUDL(self):
        if self.crudl:
            return self.crudl()
        raise Exception("Must define self.crudl")

    def getUser(self):
        if self.user:
            return self.user
        raise Exception("Must define self.user")

    def getCreatePostData(self):
        raise Exception("Missing method: %s.getCreatePostData()" % self.__class__.__name__)

    def getUpdatePostData(self):
        raise Exception("Missing method: %s.getUpdatePostData()" % self.__class__.__name__)

    def getManager(self):
        return self.getCRUDL().model.objects

    def getTestObject(self):
        if self.object:
            return self.object

        if self.getCRUDL().permissions:
            self.login(self.getUser())

        # create our object
        create_page = reverse(self.getCRUDL().url_name_for_action('create'))
        post_data = self.getCreatePostData()
        self.client.post(create_page, data=post_data)

        # find our created object
        self.object = self.getManager().get(**post_data)
        return self.object

    def testCreate(self):
        if 'create' not in self.getCRUDL().actions:
            return
        self._do_test_view('create', post_data=self.getCreatePostData())

    def testRead(self):
        if 'read' not in self.getCRUDL().actions:
            return
        self._do_test_view('read', self.getTestObject())

    def testUpdate(self):
        if 'update' not in self.getCRUDL().actions:
            return
        self._do_test_view('update', self.getTestObject(), post_data=self.getUpdatePostData())

    def testDelete(self):
        if 'delete' not in self.getCRUDL().actions:
            return
        object = self.getTestObject()
        self._do_test_view('delete', object, post_data=dict())
        self.assertEquals(0, len(self.getManager().filter(pk=object.pk)))

    def testList(self):
        if 'list' not in self.getCRUDL().actions:
            return
        # have at least one object
        self.getTestObject()
        self._do_test_view('list')

    def testCsv(self):
        if 'csv' not in self.getCRUDL().actions:
            return
        # have at least one object
        self.getTestObject()
        self._do_test_view('csv')

    def _do_test_view(self, action=None, object=None, post_data=None, query_string=None):
        url_name = self.getCRUDL().url_name_for_action(action)
        if object:
            url = reverse(url_name, args=[object.pk])
        else:
            url = reverse(url_name)

        # append our query string if we have one
        if query_string:
            url = "%s?%s" % (url, query_string)

        # make sure we are logged out before testing permissions
        self.client.logout()

        response = self.client.get(url)

        view = self.getCRUDL().view_for_action(action)
        if self.getCRUDL().permissions and view.permission is not None:
            self.assertRedirect(response, reverse("users.user_login"), msg="Page for '%s' loaded without being logged in first" % action)
            self.login(self.getUser())
            response = self.client.get(url)

        fn = "assert%sGet" % action.capitalize()
        self.assertPageGet(action, response)
        if hasattr(self, fn):
            getattr(self, fn)(response)

        if post_data is not None:
            response = self.client.post(url, data=post_data)

            self.assertPagePost(action, response)
            fn = "assert%sPost" % action.capitalize()
            if hasattr(self, fn):
                getattr(self, fn)(response)

        return response

    def assertPageGet(self, action, response):
        if response.status_code == 302:
            self.fail("'%s' resulted in an unexpected redirect to: %s" % (action, response.get('Location')))
        self.assertEquals(200, response.status_code, )

    def assertPagePost(self, action, response):
        self.assertNoFormErrors(response)
