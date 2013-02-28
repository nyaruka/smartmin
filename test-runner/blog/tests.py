from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Group
from blog.models import Post, Category
from smartmin.management import check_role_permissions
from django.utils import simplejson
from .views import PostCRUDL
from smartmin.views import smart_url
from guardian.shortcuts import assign
import settings

from smartmin.users.models import *
from datetime import date, datetime, timedelta
from django.utils import timezone

class SmartminTest(TestCase):

    def setUp(self):
        self.client = Client()

        # no groups
        self.plain = User.objects.create_user('plain', 'plain@nogroups.com', 'plain')

        # part of the editor group
        self.editor = User.objects.create_user('editor', 'editor@group.com', 'editor')
        self.editor.groups.add(Group.objects.get(name="Editors"))

        # part of the Author group
        self.author = User.objects.create_user('author', 'author@group.com', 'author')
        self.author.groups.add(Group.objects.get(name="Authors"))

        # admin user
        self.superuser = User.objects.create_user('superuser', 'superuser@group.com', 'superuser')
        self.superuser.is_superuser = True
        self.superuser.save()

        self.post = Post.objects.create(title="Test Post", body="This is the body of my first test post", tags="testing_tag", order=0,
                                        created_by=self.author, modified_by=self.author)

    def assertRedirect(self, response, url):
        self.assertEquals(302, response.status_code)
        self.assertTrue(response.get('Location', None).find(reverse('users.user_login')) != -1,
                        "Did not redirect to expected URL, expected: %s, got %s" % (url, response.get('Location', None)))

    def assertNoAccess(self, user, url):
        self.client.login(username=user.username, password=user.username)
        response = self.client.get(url)
        self.assertIsLogin(response)

    def assertHasAccess(self, user, url):
        self.client.login(username=user.username, password=user.username)
        response = self.client.get(url)
        self.assertEquals(200, response.status_code, "User '%s' does not have access to URL: %s" % (user.username, url))

    def assertIsLogin(self, response):
        self.assertRedirect(response, reverse('users.user_login'))

    def test_smart_url(self):
        self.assertEquals(reverse('blog.post_create'), smart_url("@blog.post_create"))
        self.assertEquals(reverse('blog.post_update', args=[self.post.id]), smart_url("id@blog.post_update", self.post.id))
        self.assertEquals(reverse('blog.post_create'), smart_url("/blog/post/create/"))
        self.assertEquals(reverse('blog.post_update', args=[self.post.id]), smart_url("/blog/post/update/%d/", self.post.id))

    def test_permissions(self):
        create_url = reverse('blog.post_create')

        # not logged in, no dice
        response = self.client.get(create_url)
        self.assertIsLogin(response)

        # logged in as editor, still can't create
        self.assertNoAccess(self.plain, create_url)
        self.assertNoAccess(self.editor, create_url)

        # authors and superusers can create posts
        self.assertHasAccess(self.author, create_url)
        self.assertHasAccess(self.superuser, create_url)

        # updating posts 
        update_url = reverse('blog.post_update', args=[self.post.id])

        # if not logged in can't read
        self.client.logout()
        response = self.client.get(update_url)
        self.assertIsLogin(response)

        # plain user can't see it either
        self.assertNoAccess(self.plain, update_url)

        # but editors can, as can authors and superusers
        self.assertHasAccess(self.editor, update_url)
        self.assertHasAccess(self.author, update_url)
        self.assertHasAccess(self.superuser, update_url)

        # now test reading posts
        read_url = reverse('blog.post_read', args=[self.post.id])

        # if not logged in can still read
        self.client.logout()
        response = self.client.get(read_url)
        self.assertEquals(200, response.status_code)

        # everybody else can read too
        self.assertHasAccess(self.plain, read_url)
        self.assertHasAccess(self.editor, read_url)
        self.assertHasAccess(self.author, read_url)
        self.assertHasAccess(self.superuser, read_url)

        # now grant object level permission to update a single post for anonymous user
        self.client.logout()
        anon = User.objects.get(pk=settings.ANONYMOUS_USER_ID)
        assign('blog.post_update', anon, self.post)

        response = self.client.get(update_url)
        self.assertEquals(200, response.status_code)


    def test_create(self):
        self.client.login(username='author', password='author')

        post_data = dict(title="New Post", body="This is a new post", order=1, tags="post")
        response = self.client.post(reverse('blog.post_create'), post_data, follow=True)

        # get the last post
        post = list(Post.objects.all())[-1]

        self.assertEquals("New Post", post.title)
        self.assertEquals("This is a new post", post.body)
        self.assertEquals("post", post.tags)
        self.assertEquals(self.author, post.created_by)
        self.assertEquals(self.author, post.modified_by)

    def test_messaging(self):
        self.client.login(username='author', password='author')

        post_data = dict(title="New Post", body="This is a new post", order=1, tags="post")
        response = self.client.post(reverse('blog.post_create'), post_data, follow=True)

        post = list(Post.objects.all())[-1]

        self.assertEquals(200, response.status_code)
        self.assertContains(response, "Your new post has been created.")

        post_data = dict(title="New Post", body="Updated post content", order=1, tags="post")
        response = self.client.post(reverse('blog.post_update', args=[post.id]), post_data, follow=True)

        self.assertEquals(200, response.status_code)
        self.assertContains(response, "Your blog post has been updated.")

    def test_message_tags(self):
        self.client.login(username='author', password='author')
        messages_url = reverse('blog.post_messages')
        response = self.client.get(messages_url)
        self.assertIn('<div class="alert alert-error">', response.content)
        self.assertIn('<div class="alert alert-success">', response.content)
        self.assertIn('<div class="alert alert-info">', response.content)
        self.assertIn('<div class="alert alert-warning">', response.content)

    def test_template_name(self):
        self.client.login(username='author', password='author')
        response = self.client.get(reverse('blog.post_list'))
        self.assertEquals(['blog/post_list.html', 'smartmin/list.html'], response.template_name)

    def test_ordering(self):
        post1 = Post.objects.create(title="A First Post", body="Post Body", order=3, tags="post",
                                    created_by=self.author, modified_by=self.author)
        post2 = Post.objects.create(title="A Second Post", body="Post Body", order=5, tags="post",
                                    created_by=self.superuser, modified_by=self.superuser)
        post3 = Post.objects.create(title="A Third Post", body="Post Body", order=1, tags="post",
                                    created_by=self.author, modified_by=self.author)
        post4 = Post.objects.create(title="A Fourth Post", body="Post Body", order=3, tags="post",
                                    created_by=self.superuser, modified_by=self.superuser)

        self.client.login(username='author', password='author')

        response = self.client.get(reverse('blog.post_list'))
        posts = response.context['post_list']

        self.assertEquals(post1, posts[0])
        self.assertEquals(post4, posts[1])
        self.assertEquals(post2, posts[2])
        self.assertEquals(post3, posts[3])
        self.assertEquals(self.post, posts[4])

        response = self.client.get(reverse('blog.post_author'))
        posts = response.context['post_list']

        self.assertEquals(self.post, posts[0])
        self.assertEquals(post3, posts[1])
        self.assertEquals(post1, posts[2])
        self.assertEquals(post4, posts[3])
        self.assertEquals(post2, posts[4])

        # get our view as json
        response = self.client.get(reverse('blog.post_list') + "?_format=json")

        # parse the json
        json_list = simplejson.loads(response.content)
        self.assertEquals(5, len(json_list))
        self.assertEquals(post1.title, json_list[0]['title'])

        # ask for select2 format
        response = self.client.get(reverse('blog.post_list') + "?_format=select2")
        select2 = simplejson.loads(response.content)
        self.assertTrue('results' in select2)
        self.assertEquals(5, len(select2['results']))

        
        
    def test_success_url(self):
        self.client.login(username='author', password='author')

        post_data = dict(title="New Post", body="This is a new post", order=1, tags="post")
        response = self.client.post(reverse('blog.post_create'), post_data, follow=True)

        self.assertEquals(reverse('blog.post_list'), response.request['PATH_INFO'])

    def test_submit_button_name(self):
        self.client.login(username='author', password='author')

        response = self.client.get(reverse('blog.post_create'))
        self.assertContains(response, "Create New Post")

    def test_excludes(self):
        self.client.login(username='author', password='author')

        # this view excludes tags with the default form
        response = self.client.get(reverse('blog.post_exclude', args=[self.post.id]))
        self.assertEquals(0, response.content.count('tags'))

        # this view excludes tags included in a custom form
        response = self.client.get(reverse('blog.post_exclude2', args=[self.post.id]))
        self.assertEquals(0, response.content.count('tags'))

    def test_readonly(self):
        self.client.login(username='author', password='author')

        # this view should have our tags field be readonly
        response = self.client.get(reverse('blog.post_readonly', args=[self.post.id]))
        self.assertEquals(1, response.content.count('testing_tag'))
        self.assertEquals(1, response.content.count('Tags'))
        self.assertEquals(0, response.content.count('input id="id_tags"'))

        # this view should also have our tags field be readonly, but it does so on a custom form
        response = self.client.get(reverse('blog.post_readonly2', args=[self.post.id]))
        self.assertEquals(1, response.content.count('testing_tag'))
        self.assertEquals(1, response.content.count('Tags'))
        self.assertEquals(0, response.content.count('input id="id_tags"'))


    def test_integrity_error(self):
        self.client.login(username='author', password='author')

        first_category = Category.objects.create(name="History", created_by=self.author, modified_by=self.author)

        post_data = dict(name="History")
        response = self.client.post(reverse('blog.category_create'), post_data)

        # should get a plain 200
        self.assertEquals(200, response.status_code)

        # should have one error (our integrity error)
        self.assertEquals(1, len(response.context['form'].errors))

    def test_version(self):
        # TODO: for whatever reason coverage refuses to belief this covers the __init__.py in smartmin
        import smartmin
        self.assertEquals('1.4.1', smartmin.__version__)

    def test_management(self):
        authors = Group.objects.get(name="Authors")

        # reduce our permission set to not include categories
        permissions =  ('blog.post.*', 'blog.post.too.many.dots', 'blog.category.not_valid_either', 'blog.', 'blog.foo.*')

        self.assertEquals(16, authors.permissions.all().count())

        # check that they are reassigned
        check_role_permissions(authors, permissions, authors.permissions.all())

        # removing all category actions should bring us to 10
        self.assertEquals(11, authors.permissions.all().count())


    def test_smart_model(self):
        p1 = Post.objects.create(title="First Post", body="First Post body", order=1, tags="first",
                                 created_by=self.author, modified_by=self.author)
        p2 = Post.objects.create(title="Second Post", body="Second Post body", order=1, tags="second",
                                 created_by=self.author, modified_by=self.author)

        self.assertEquals(3, Post.objects.all().count())
        self.assertEquals(3, Post.active.all().count())

        # make p2 inactive
        p2.is_active = False
        p2.save()

        self.assertEquals(3, Post.objects.all().count())
        self.assertEquals(2, Post.active.all().count())

class UserTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_user('superuser', 'superuser@group.com', 'superuser')
        self.superuser.is_superuser = True
        self.superuser.save()

       
    def test_crudl(self):
        self.client.login(username='superuser', password='superuser')

        post_data = dict(username='steve',
                         new_password='apple',
                         first_name='Steve',
                         last_name='Jobs',
                         groups=Group.objects.get(name='Administrator').id,
                         email='steve@apple.com')

        response = self.client.post(reverse('users.user_create'), post_data, follow=True)
        self.assertEquals(200, response.status_code)

        # we should have failed due to our password not being long enough
        self.assertTrue('new_password' in response.context['form'].errors)

        # try with a longer password but without our requirements (8 chars)
        post_data['new_password'] = 'password'
        response = self.client.post(reverse('users.user_create'), post_data, follow=True)
        self.assertEquals(200, response.status_code)
        self.assertTrue('new_password' in response.context['form'].errors)

        # try with one capital letter
        post_data['new_password'] = 'Password'
        response = self.client.post(reverse('users.user_create'), post_data, follow=True)
        self.assertEquals(200, response.status_code)
        self.assertTrue('new_password' in response.context['form'].errors)

        # ok, finally with a zero in there too, this one should pass
        post_data['new_password'] = 'Passw0rd'
        response = self.client.post(reverse('users.user_create'), post_data, follow=True)
        self.assertEquals(200, response.status_code)
        self.assertTrue('form' not in response.context)

        # make sure the user was created
        steve = User.objects.get(username='steve')

        # can't create another with the same email though
        post_data['username'] = 'steve2'
        response = self.client.post(reverse('users.user_create'), post_data, follow=True)
        self.assertEquals(200, response.status_code)
        self.assertTrue('email' in response.context['form'].errors)

        # create another user manually, make him inactive
        woz = User.objects.create_user('woz', 'woz@apple.com', 'woz')
        woz.is_active = False
        woz.save()

        # list our users
        response = self.client.get(reverse('users.user_list'))
        users = response.context['user_list']

        # results should be sorted by username
        self.assertEquals(2, len(users))
        self.assertEquals(steve, users[0])
        self.assertEquals(woz, users[1])

        # check our content too
        self.assertContains(response, 'woz')
        self.assertContains(response, 'steve')

        # update steve, put him in a different group and change his password
        post_data['groups'] = Group.objects.get(name='Editors').id
        post_data['new_password'] = 'googleIsNumber1'

        # need is active here or steve will be marked inactive
        post_data['is_active'] = '1'
        post_data['username'] = 'steve'

        response = self.client.post(reverse('users.user_update', args=[steve.id]), post_data, follow=True)
        self.assertEquals(200, response.status_code)
        self.assertTrue('form' not in response.context)

        # check that steve's group changed
        steve = User.objects.get(pk=steve.id)
        groups = steve.groups.all()
        self.assertEquals(1, len(groups))
        self.assertEquals(Group.objects.get(name='Editors'), groups[0])

        # assert steve can login with 'google' now
        self.assertTrue(self.client.login(username='steve', password='googleIsNumber1'))

        # test user profile action
        # logout first
        self.client.logout()

        # login as super user
        self.assertTrue(self.client.login(username='superuser', password='superuser'))

        # as a super user mimic Steve
        response = self.client.post(reverse('users.user_mimic', args=[steve.id]), follow=True)

        # check if the logged in user is steve now
        self.assertEquals(response.context['user'].username, 'steve')
        self.assertEquals(response.request['PATH_INFO'], settings.LOGIN_REDIRECT_URL)

        # now that steve is the one logged in can he mimic woz?
        response = self.client.get(reverse('users.user_mimic', args=[woz.id]), follow=True)
        self.assertEquals(response.request['PATH_INFO'], settings.LOGIN_URL)

        # login as super user
        self.assertTrue(self.client.login(username='superuser', password='superuser'))

        # check is access his profile
        response = self.client.get(reverse('users.user_profile', args=[self.superuser.id]))
        self.assertEquals(200, response.status_code)
        self.assertEquals(reverse('users.user_profile', args=[self.superuser.id]), response.request['PATH_INFO'])

        # create just a plain  user
        plain = User.objects.create_user('plain', 'plain@nogroups.com', 'plain')

        # login as a simple plain user
        self.assertTrue(self.client.login(username='plain', password='plain'))
        
        # check is access his profile, should not since plain users don't have that permission
        response = self.client.get(reverse('users.user_profile', args=[plain.id]))
        self.assertEquals(302, response.status_code)

        # log in as an editor instead
        self.assertTrue(self.client.login(username='steve', password='googleIsNumber1'))
        response = self.client.get(reverse('users.user_profile', args=[steve.id]))
        self.assertEquals(reverse('users.user_profile', args=[steve.id]), response.request['PATH_INFO'])
        
        # check if we are at the right form
        self.assertEquals("UserProfileForm", type(response.context['form']).__name__)

        response = self.client.post(reverse('users.user_profile', args=[steve.id]), {}, follow=True)

        # check which field he have access to
        self.assertEquals(6, len(response.context['form'].visible_fields()))

        # doesn't include readonly fields on post
        self.assertNotIn("username", response.context['form'].fields)

        # check if he can fill a wrong old password
        post_data = dict(old_password="plainwrong", new_password="NewPassword1")
        response = self.client.post(reverse('users.user_profile', args=[steve.id]), post_data)
        self.assertTrue('old_password' in response.context['form'].errors)

        # check if he can mismatch new password and its confirmation
        post_data = dict(old_password="plain", new_password="NewPassword1", confirm_new_password="confirmnewpassword")
        response = self.client.post(reverse('users.user_profile', args=[steve.id]), post_data)

        # check if he can fill old and new password only without the confirm new password
        post_data = dict(old_password="plain", new_password="NewPassword1")
        response = self.client.post(reverse('users.user_profile', args=[steve.id]), post_data)
        self.assertIn("Confirm the new password by filling the this field", response.content)

        # actually change the password
        post_data = dict(old_password="googleIsNumber1", new_password="NewPassword1", confirm_new_password="NewPassword1")
        response = self.client.post(reverse('users.user_profile', args=[steve.id]), post_data)

        # assert new password works
        self.assertTrue(self.client.login(username='steve', password='NewPassword1'))

        # see whether we can change our email without a password
        post_data = dict(email="new@foo.com")
        response = self.client.post(reverse('users.user_profile', args=[steve.id]), post_data)
        self.assertTrue('old_password' in response.context['form'].errors)

        # but with the new password we can
        post_data = dict(email="new@foo.com", old_password='NewPassword1')
        response = self.client.post(reverse('users.user_profile', args=[steve.id]), post_data)
        self.assertTrue(User.objects.get(email='new@foo.com'))

    def test_token(self):
        # create a user user1 with password user1 and email user1@user1.com
        user1 = User.objects.create_user("user1", 'user1@user1.com', 'user1')
 
        # be sure no one is logged in
        self.client.logout()

        # test our user can log in
        self.assertTrue(self.client.login(username='user1', password='user1'))
        self.client.logout()

        # initialise the process of recovering password by clicking the forget
        # password link and fill the form with the email associated with the account
        
        # invalid user 
        forget_url = reverse('users.user_forget')
    
        post_data = dict()
        post_data['email'] = 'nouser@nouser.com'
        
        response = self.client.post(forget_url, post_data, follow=True)
        
        # email form submitted successfully
        self.assertEquals(200, response.status_code)

        # email with valid user
        forget_url = reverse('users.user_forget')

        post_data = dict()
        post_data['email'] = 'user1@user1.com'
        
        response = self.client.post(forget_url, post_data, follow=True)
        
        # email form submitted successfully
        self.assertEquals(200, response.status_code)

        # now there is a token generated
        recovery_token = RecoveryToken.objects.get(user=user1)
        self.assertNotEquals(None,recovery_token.token)

        # still the user can login with usual password and cannot login with the new password test
        self.assertTrue(self.client.login(username='user1', password='user1'))
        self.client.logout()
        self.assertFalse(self.client.login(username='user1', password='user1_newpasswd'))
        self.client.logout()
        # user click the link provided in mail
        
        recover_url = reverse('users.user_recover', args=[recovery_token.token])
        
        post_data = dict()
        post_data['new_password'] = 'user1_newpasswd'
        post_data['confirm_new_password'] = ''

        response = self.client.post(recover_url, post_data, follow=True)
        self.assertIn("This field is required.", response.content)

        recover_url = reverse('users.user_recover', args=[recovery_token.token])
        
        post_data = dict()
        post_data['new_password'] = 'user1_newpasswd'
        post_data['confirm_new_password'] = 'user1_passwd_dont_match'

        response = self.client.post(recover_url, post_data, follow=True)
        self.assertIn('confirm_new_password', response.context['form'].errors)

        # if the token is valid we get a form to fill with new password
        recover_url = reverse('users.user_recover', args=[recovery_token.token])
        
        post_data = dict()
        post_data['new_password'] = 'user1_newpasswd'
        post_data['confirm_new_password'] = 'user1_newpasswd'

        response = self.client.post(recover_url, post_data, follow=True)
        # form submitted successfull
        self.assertEquals(200, response.status_code)
        
        # now the user cannot login with the old password but can login with the new one
        self.assertFalse(self.client.login(username='user1', password='user1'))
        self.client.logout()
        self.assertTrue(self.client.login(username='user1', password='user1_newpasswd'))
        self.client.logout()

        # second click on the link
        recover_url = reverse('users.user_recover', args=[recovery_token.token])
        
        post_data = dict()
        post_data['new_password'] = 'user1_newpasswd_2'
        post_data['confirm_new_password'] = 'user1_newpasswd_2'

        response = self.client.post(recover_url, post_data, follow=True)
        # form submitted successfull
        self.assertEquals(200, response.status_code)
        
        # password must not change
        self.assertFalse(self.client.login(username='user1', password='user1_newpasswd_2'))
        self.client.logout()
        self.assertTrue(self.client.login(username='user1', password='user1_newpasswd'))
        self.client.logout()

    def test_lockout(self):
        # first create a user to use on the test
        user2 = User.objects.create_user("user2", 'user2@user2.com', 'user2')

        #be sure no user os logged in
        self.client.logout()

        # login page
        login_url = reverse('users.user_login')

        post_data = dict()
        post_data['username'] = 'user2'
        post_data['password'] = 'wrongpassword'

        # try to log in four times
        for i in range(4):
            response = self.client.post(login_url,post_data)
            self.assertFalse( response.context['user'].is_authenticated())

        # on the fifth failed login we get redirected
        response = self.client.post(login_url, post_data)
        self.assertEquals(302, response.status_code)

class UserTestCase(TestCase):

    def test_reverse(self):
        # the reverse tag here should be blog.user_list, not auth.user_list, since the 
        # CRUDL objects is defined in the blog app
        response = self.client.get(reverse('blog.user_list'))
        self.assertEquals(200, response.status_code)

        # also make sure the proper template is used (should be /blog/user_list.html)
        self.assertContains(response, "Custom Pre-Content")

class TagTestCase(TestCase):

    def setUp(self):
        self.crudl = PostCRUDL()
        self.list_view = self.crudl.view_for_action('list')()
        self.read_view = self.crudl.view_for_action('read')()

        self.plain = User.objects.create_user('plain', 'plain@nogroups.com', 'plain')

        self.author = User.objects.create_user('author', 'author@group.com', 'author')
        self.author.groups.add(Group.objects.get(name="Authors"))

        self.post = Post.objects.create(title="First Post", body="My First Post", tags="first", order=1,
                                        created_by=self.author, modified_by=self.author)

    def test_value_from_view(self):
        from smartmin.templatetags.smartmin import get_value_from_view
        import pytz

        context = dict(view=self.read_view, object=self.post)
        self.assertEquals(self.post.title, get_value_from_view(context, 'title'))
        local_created = self.post.created_on.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('Africa/Kigali'))
        self.assertEquals(local_created.strftime("%b %d, %Y %H:%M"), get_value_from_view(context, 'created_on'))

    def test_view_as_json(self):
        from smartmin.templatetags.smartmin import view_as_json

        self.list_view.object_list = Post.objects.all()
        context = dict(view=self.list_view)

        foo = view_as_json(context)
        json = simplejson.loads(view_as_json(context))
        self.assertEquals(1, len(json))
        self.assertEquals(self.post.title, json[0]['title'])

    def test_get(self):
        from smartmin.templatetags.smartmin import get

        test_dict = dict(key="value")

        self.assertEquals("value", get(test_dict, 'key'))
        self.assertEquals("", get(test_dict, 'not_there'))

    def test_map(self):
        from smartmin.templatetags.smartmin import map
        self.assertEquals("title: First Post id: 1", map("title: %(title)s id: %(id)d", self.post))

    def test_gmail_time(self):
        import pytz
        from smartmin.templatetags.smartmin import gmail_time

        # given the time as now, should display "Hour:Minutes AM|PM" eg. "5:05 pm"
        now = timezone.now()
        modified_now = now.replace(hour=17, minute=05)
        self.assertEquals("7:05 pm", gmail_time(modified_now))

        # given the time beyond 12 hours ago within the same month, should display "MonthName DayOfMonth" eg. "Jan 2"
        feb_2 = datetime(2013, 02, 02, 17, 05, 00, 00).replace(tzinfo = pytz.utc)
        self.assertEquals("Feb 2", gmail_time(feb_2))

        # given the time beyond the current month, should display "DayOfMonth/Month/Year" eg. "2/1/2013"
        jan_2 = datetime(2013, 01, 02, 17, 05, 00, 00).replace(tzinfo = pytz.utc)
        self.assertEquals("2/1/13", gmail_time(jan_2))

    def test_user_as_string(self):
        from smartmin.templatetags.smartmin import user_as_string
        
        # plain user have both first and last names
        self.plain.first_name = "Mr"
        self.plain.last_name = "Chips"
        self.plain.save()
        self.assertEquals("Mr Chips", user_as_string(self.plain))

        # change this user to have firstname as an empty string
        self.plain.first_name = ''
        self.plain.save()
        self.assertEquals("Chips", user_as_string(self.plain))

        # change this user to have lastname as an empty string
        self.plain.last_name = ''
        self.plain.first_name = 'Mr'
        self.plain.save()
        self.assertEquals("Mr", user_as_string(self.plain))

        # change this user to have both first and last being empty strings
        self.plain.last_name = ''
        self.plain.first_name = ''
        self.plain.save()
        self.assertEquals("plain", user_as_string(self.plain))

class UserLockoutTestCase(TestCase):

    def setUp(self):
        self.plain = User.objects.create_user('plain', 'plain@nogroups.com', 'plain')

        self.superuser = User.objects.create_user('superuser', 'superuser@group.com', 'superuser')
        self.superuser.is_superuser = True
        self.superuser.save()

    def testBadLogin(self):
        post_data = dict(email='foo', password='blah')
        response = self.client.post(reverse('users.user_login'), post_data)

        self.assertEquals(200, response.status_code)
        self.assertTrue('username' in response.context['form'].errors)

    def doLockout(self):
        # go to the login page
        response = self.client.get(reverse('users.user_login'))

        # make sure there is no reset link
        self.assertTrue(response.content.find(reverse('users.user_forget')) == -1);

        # also make sure we can't actually do a reset
        post_data = dict(email="nicpottier@gmail.com")
        response = self.client.post(reverse('users.user_forget'), post_data)

        self.assertTrue('email' in response.context['form'].errors)

        # try logging in four times, get account locked
        for i in range(4):
            post_data = dict(username='plain', password='plain2')
            response = self.client.post(reverse('users.user_login'), post_data)
            self.assertTrue(response.context['form'].errors)

        # on the fifth time it should fail
        response = self.client.post(reverse('users.user_login'), post_data, follow=True)
        self.assertFalse(response.context['user'].is_authenticated())
        self.assertTrue(response.content.find(reverse('users.user_forget')) == -1);

        # even with right password, no dice
        post_data = dict(username='plain', password='plain')
        response = self.client.post(reverse('users.user_login'), post_data, follow=True)
        self.assertFalse(response.context['user'].is_authenticated())
        self.assertTrue(response.content.find(reverse('users.user_forget')) == -1);

    def testNoRecovery(self):
        with self.settings(USER_ALLOW_EMAIL_RECOVERY=False):
            self.doLockout()

            post_data = dict(username='plain', password='plain')
            response = self.client.post(reverse('users.user_login'), post_data, follow=True)

            # should say something about 10 minutes
            self.assertContains(response, "10 minutes")

            # move all our lockout events to 11 minutes in the past
            ten_minutes = timedelta(minutes=10)
            for failed in FailedLogin.objects.filter(user=self.plain):
                failed.failed_on = failed.failed_on - ten_minutes
                failed.save()

            # should now be able to log in
            response = self.client.post(reverse('users.user_login'), post_data, follow=True)
            self.assertTrue( response.context['user'].is_authenticated())

    def testNoRecoveryNoTimeout(self):
        with self.settings(USER_ALLOW_EMAIL_RECOVERY=False, USER_LOCKOUT_TIMEOUT=-1):
            # get ourselves locked out
            self.doLockout()

            post_data = dict(lusername='plain', password='plain')
            response = self.client.post(reverse('users.user_login'), post_data, follow=True)

            # should say nothing about 10 minutes
            self.assertTrue(response.content.find("10 minutes") == -1)

            # move all our lockout events to 11 minutes in the past
            ten_minutes = timedelta(minutes=10)
            for failed in FailedLogin.objects.filter(user=self.plain):
                failed.failed_on = failed.failed_on - ten_minutes
                failed.save()

            # should still have no dice on trying to log in
            post_data = dict(username='plain', password='plain')
            response = self.client.post(reverse('users.user_login'), post_data, follow=True)
            self.assertContains(response, "cannot log")
            self.assertTrue(response.content.find(reverse('users.user_forget')) == -1);

            # log in as superuser
            response = self.client.post(reverse('users.user_login'), 
                                        dict(username='superuser', password='superuser'))

            # go edit our 'plain' user
            response = self.client.get(reverse('users.user_update', args=[self.plain.id]))

            # change the password
            post_data = dict(new_password='Password1', username='plain', groups='1', is_active='1')
            response = self.client.post(reverse('users.user_update', args=[self.plain.id]),
                                        post_data)

            # assert our lockouts got cleared
            self.assertFalse(FailedLogin.objects.filter(user=self.plain))

            # the user should be able to log in now
            self.client.logout()

            post_data = dict(username='plain', password='Password1')
            response = self.client.post(reverse('users.user_login'), post_data, follow=True)
            self.assertTrue(response.context['user'].is_authenticated())

class PasswordExpirationTestCase(TestCase):

    def setUp(self):
        self.plain = User.objects.create_user('plain', 'plain@nogroups.com', 'Password1')
        self.plain.groups.add(Group.objects.get(name="Editors"))

    def testNoExpiration(self):
        # create a fake password set 90 days ago
        ninety_days_ago = timezone.now() - timedelta(days=90)
        history = PasswordHistory.objects.create(user=self.plain,
                                                 password="asdfasdf")

        history.set_on = ninety_days_ago
        history.save()

        # log in
        self.client.logout()
        post_data = dict(username='plain', password='Password1')
        response = self.client.post(reverse('users.user_login'), post_data, follow=True)
        self.assertTrue(response.context['user'].is_authenticated())

        # we shouldn't be on a page asking us for a new password
        self.assertFalse('form' in response.context)

    def testPasswordRepeat(self):
        history = PasswordHistory.objects.create(user=self.plain,
                                                 password=self.plain.password)        

        with self.settings(USER_PASSWORD_REPEAT_WINDOW=365):
            self.assertTrue(PasswordHistory.is_password_repeat(self.plain, "Password1"))
            self.assertFalse(PasswordHistory.is_password_repeat(self.plain, "anotherpassword"))

            # move our history into the past
            history.set_on = timezone.now() - timedelta(days=366)
            history.save()

            # still a repeat because it is our current password
            self.assertTrue(PasswordHistory.is_password_repeat(self.plain, "Password1"))

            # change our password under the covers
            self.plain.set_password("my new password")

            # now this one is fine
            self.assertFalse(PasswordHistory.is_password_repeat(self.plain, "Password1"))

        with self.settings(USER_PASSWORD_REPEAT_WINDOW=-1):
            history.set_on = timezone.now()
            history.save()

            self.assertFalse(PasswordHistory.is_password_repeat(self.plain, "Password1"))

    def testExpiration(self):
        with self.settings(USER_PASSWORD_EXPIRATION=60, USER_PASSWORD_REPEAT_WINDOW=365):
            # create a fake password set 90 days ago
            ninety_days_ago = timezone.now() - timedelta(days=90)
            history = PasswordHistory.objects.create(user=self.plain,
                                                     password=self.plain.password)

            history.set_on = ninety_days_ago
            history.save()
            
            # log in
            self.client.logout()
            post_data = dict(username='plain', password='Password1')
            response = self.client.post(reverse('users.user_login'), post_data, follow=True)

            # assert we are being taken to our new password page
            self.assertTrue('form' in response.context)
            self.assertTrue('new_password' in response.context['form'].fields)

            # try to go to a different page
            response = self.client.get(reverse('blog.post_list'), follow=True)

            # redirected again
            self.assertTrue('form' in response.context)
            self.assertTrue('new_password' in response.context['form'].fields)

            # ok, set our new password
            post_data = dict(old_password='Password1', new_password='Password1', confirm_new_password='Password1')
            response = self.client.post(reverse('users.user_newpassword', args=[0]), post_data)

            # we should get a failure that our new password is a repeat
            self.assertTrue('confirm_new_password' in response.context['form'].errors)

            # use a different password
            post_data = dict(old_password='Password1', new_password='Password2', confirm_new_password='Password2')
            response = self.client.post(reverse('users.user_newpassword', args=[0]), post_data)

            # should be redirected to the normal redirect page
            self.assertEquals(302, response.status_code)
            self.assertTrue(response['location'].find(reverse('blog.post_list')) > 0)

            # should now have two password histories
            self.assertEquals(2, PasswordHistory.objects.filter(user=self.plain).count())

            # should be able to log in normally
            self.client.logout()

            post_data = dict(username='plain', password='Password2')
            response = self.client.post(reverse('users.user_login'), post_data)
            
            self.assertEquals(302, response.status_code)
            self.assertTrue(response['location'].find(reverse('blog.post_list')) > 0)
