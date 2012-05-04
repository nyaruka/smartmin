from urlparse import urlparse
from django.contrib.auth.models import Group, User
from django.core.urlresolvers import reverse, NoReverseMatch
from django.test.client import Client
from django.test.testcases import TestCase


class SmartminTest(TestCase):

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

    def do_test_crudl(self, crudl, user=None):

        crudl = crudl()

        login_page = reverse('users.user_login')
        if crudl.permissions:

            for action in crudl.actions:
                try :
                    url = reverse(crudl.url_name_for_action(action))
                    self.assertRedirect(self.client.get(url), login_page, msg="Accessed page without logging in: %s" % url)
                except NoReverseMatch:
                    pass

            # now login
            self.login(user=user)

            for action in crudl.actions:
                try :
                    url = reverse(crudl.url_name_for_action(action))
                    self.assertEquals(200, self.client.get(url).status_code, msg="Couldn't load after logging in: %s" % url)
                except NoReverseMatch:
                    pass


    def old_do_test_crudl(self, crudl, post_data,
                      update_data=None, filter_data=None, username=None, redirect=None, asserts=None):

        crudl = crudl()
        crudl.module_name = crudl.app_name

        # start with a fresh client to test logged out case
        self.client = Client()

        # handy url shortcuts
        create = crudl.url_name_for_action('create')
        read = crudl.url_name_for_action('read')
        update = crudl.url_name_for_action('update')
        delete = crudl.url_name_for_action('delete')
        list = crudl.url_name_for_action('list')

        object = None



        # can't see the pages without first logging in
        if crudl.permissions and 'create' in crudl.actions:
            resp = self.client.get(reverse(create))
            self.assertRedirect(reverse('users.user_login'), resp, "Was able to reach Create page without logging in for %s" % crudl)

        if crudl.permissions and 'list' in crudl.actions:
            resp = self.client.get(reverse(list))
            self.assertRedirect(reverse('users.user_login'), resp, "Was able to reach List page without logging in for %s" % crudl)

        # login and now and get on with it
        if username:
            self.login(username)

        if 'list' in crudl.actions:
            resp = self.client.get(reverse(list))
            self.assertEquals(200, resp.status_code, msg="Couldn't reach List page for %s" % crudl.__class__.__name__)

        # can't imagine a crudl without a create
        if 'create' in crudl.actions:
            resp = self.client.get(reverse(create))
            self.assertEquals(200, resp.status_code, msg="Couldn't reach create page for %s" % crudl.model_name)

            # post to our create page
            resp = self.client.post(reverse(create), post_data)

            # we should always redirect on create, if it's not we have form errors
            if resp.status_code != 302 and len(resp.context['form'].errors) > 0:
                self.fail("Form errors: %s" % dict(resp.context['form'].errors))

            if redirect:
                self.assertRedirect(redirect, resp, msg="Couldn't create for %s" % crudl.model_name)
            elif 'list' in crudl.actions:
                self.assertRedirect(reverse(list), resp, msg="Couldn't create for %s" % crudl.model_name)

            # fall back to post_data if no filter data is provided
            if not filter_data:
                filter_data = post_data

            # pull our object out according to our filter data
            results = None
            for filter in filter_data.items():
                if not results:
                    results = crudl.model.objects.filter(filter)
                else:
                    results = results.filter(filter)

            self.assertEquals(1, len(results))
            object = results[0]

            # check that our object now exists on the list page
            if 'list' in crudl.actions:
                resp = self.client.get(reverse(list), post_data)
                if asserts:
                    for value in asserts:
                        self.assertContains(resp, value)

                else:
                    for key, value in filter_data.items():
                        self.assertContains(resp, value)

        # view our read page, not all crudls do read
        if 'read' in crudl.actions and object:
            resp = self.client.get(reverse(read, args=[object.pk]))
            self.assertEquals(200, resp.status_code)

            if asserts:
                for value in asserts:
                    self.assertContains(resp, value)
            else:
                # check that all of our creation data is present on the read page
                for key, value in post_data.items():
                    self.assertContains(resp, value)

        # try to update our crudl
        if 'update' in crudl.actions:

            if not update_data:
                update_data = post_data

            # merge our update data into our post data
            for key, value in update_data.items():
                post_data[key] = value

            # can we get to the update page?
            resp = self.client.get(reverse(update, args=[object.pk]))
            self.assertEquals(200, resp.status_code)

            # post to our update page
            resp = self.client.post(reverse(update, args=[object.pk]), post_data)

            # we should always redirect on update, if it's not we have form errors
            if resp.status_code != 302 and len(resp.context['form'].errors) > 0:
                self.fail("Form errors: %s" % dict(resp.context['form'].errors))

        # view our delete page, not all crudls do delete
        if 'delete' in crudl.actions:
            resp = self.client.get(reverse(delete, args=[object.pk]))
            self.assertEquals(200, resp.status_code)

            resp = self.client.post(reverse(delete, args=[object.pk]))
            self.assertRedirect(reverse(list), resp,
                msg="Couldn't delete for %s" % crudl.model)

            self.assertNotContains(resp, object)


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

    def assertNoFormErrors(self, response):
        if response.status_code == 200 and 'form' in response.context:
            form = response.context['form']

            if not form.is_valid():
                errors = []
                for k,v in form.errors.iteritems():
                    errors.append("%s=%s" % (k,v.as_text()))
                self.fail("Create failed with form errors: %s" % ",".join(errors))

    def getCreatePostData(self):
        raise Exception("Missing method: %s.getCreatePostData()" % self.__class__.__name__)

    def getUpdatePostData(self):
        raise Exception("Missing method: %s.getUpdatePostData()" % self.__class__.__name__)

    def assertPreCreate(self, response):
        self.assertEquals(200, response.status_code, msg="Couldn't load create page")

    def assertPostCreate(self, response):
        self.assertNoFormErrors(response)
        self.assertEquals(302, response.status_code)

    def assertPreUpdate(self, response):
        self.assertEquals(200, response.status_code, msg="Couldn't load update page")

    def assertPostUpdate(self, response):
        self.assertNoFormErrors(response)
        self.assertEquals(302, response.status_code)

    def getObjectToUpdate(self):

        if self.object:
            return self.object

        if self.getCRUDL().permissions:
            self.login(self.getUser())

        # create our object
        create_page = reverse(self.getCRUDL().url_name_for_action('create'))
        post_data = self.getCreatePostData()
        self.assertPostCreate(self.client.post(create_page, data=post_data))

        # find our created object
        self.object = self.getCRUDL().model.objects.get(**post_data)
        return self.object

    def testCreate(self):

        # print "Running %s.testCreate()" % self.__class__.__name__
        # only test create if it's in our action list
        if 'create' not in self.getCRUDL().actions:
            # print "No create action for %s" % self.getCRUDL().__class__.__name__
            return

        # check that we have proper permissions
        create_page = reverse(self.getCRUDL().url_name_for_action('create'))
        response = self.client.get(create_page)
        if self.getCRUDL().permissions:
            self.assertRedirect(response, reverse("users.user_login"), msg="Create page loaded without being logged in first")
            self.login(self.getUser())
            response = self.client.get(create_page)

        # create our object
        self.assertPreCreate(response)
        post_data = self.getCreatePostData()
        self.assertPostCreate(self.client.post(create_page, data=post_data))

    def testUpdate(self):

        # print "Running %s.testUpdate()" % self.__class__.__name__
        # only test create if it's in our action list
        if 'update' not in self.getCRUDL().actions:
            # print "No update action for %s" % self.getCRUDL().__class__.__name__
            return

        # get the object we are going to update
        update_object = self.getObjectToUpdate()

        # make sure we are logged out before testing permissions
        self.client.logout()
        update_page = reverse(self.getCRUDL().url_name_for_action('update'), args=[self.getObjectToUpdate().pk])

        response = self.client.get(update_page)
        if self.getCRUDL().permissions:
            self.assertRedirect(response, reverse("users.user_login"), msg="Update page loaded without being logged in first")
            self.login(self.getUser())
            response = self.client.get(update_page)

        self.assertPreUpdate(response)
        post_data = self.getUpdatePostData()
        self.assertPostUpdate(self.client.post(update_page, data=post_data))
