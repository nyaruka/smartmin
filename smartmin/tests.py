from urlparse import urlparse
from django.contrib.auth.models import Group, User
from django.core.urlresolvers import reverse
from django.test.testcases import TestCase


class SmartminTest(TestCase):

    def fetch_protected(self, url, user, post_data=None):
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
        response = self.client.get(url)
        self.assertEquals(200, response.status_code)

        # now try and give it a post
        if post_data is not None:
            response = self.client.post(url, data=post_data)
            self.assertNoFormErrors(response, post_data)
            self.assertEquals(302, response.status_code)

        return response

    def assertRedirect(self, response, url, msg=None):
        self.assertEquals(302, response.status_code, msg=msg)
        segments = urlparse(response.get('Location', None))
        self.assertEquals(segments.path, url, msg=msg)

    def create_user(self, username, group_names=None):
        # Create a user to run our CRUDL tests
        user = User.objects.create_user(username, "%s@nyaruka.com" % username)
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
                for k,v in form.errors.iteritems():
                    errors.append("%s=%s" % (k,v.as_text()))
                self.fail("Create failed with form errors: %s, Posted: %s" % (",".join(errors), post_data))

class _CRUDLTest(SmartminTest):

    crudl = None
    user = None
    object = None

    def setUp(self):
        self.crudl = None
        self.user = None
        super(_CRUDLTest, self).setUp()

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
        self.object = self.getCRUDL().model.objects.get(**post_data)
        return self.object

    def testCreate(self):
        if 'create' not in self.getCRUDL().actions:
            return
        self.do_test_view('create', post_data=self.getCreatePostData())

    def testRead(self):
        if 'read' not in self.getCRUDL().actions:
            return
        self.do_test_view('read', self.getTestObject())

    def testUpdate(self):
        if 'update' not in self.getCRUDL().actions:
            return
        self.do_test_view('update', self.getTestObject(), post_data=self.getUpdatePostData())

    def testDelete(self):
        if 'delete' not in self.getCRUDL().actions:
            return
        object = self.getTestObject()
        self.do_test_view('delete', object, post_data=dict())
        self.assertEquals(0, len(self.getCRUDL().model.objects.filter(pk=object.pk)))

    def testList(self):
        if 'list' not in self.getCRUDL().actions:
            return
        # have at least one object
        self.getTestObject()
        self.do_test_view('list')

    def testCsv(self):
        if 'csv' not in self.getCRUDL().actions:
            return
        # have at least one object
        self.getTestObject()
        self.do_test_view('csv')

    def do_test_view(self, action, object=None, post_data=None, query_string=None):

        # print "testing view %s.%s" % (self.__class__.__name__, action)

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
        if self.getCRUDL().permissions:
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
