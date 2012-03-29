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
        self.assertEquals('1.4.0', smartmin.__version__)

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

        response = self.client.post(reverse('smartmin.user_create'), post_data, follow=True)
        self.assertEquals(200, response.status_code)
        self.assertTrue('form' not in response.context)

        # make sure the user was created
        steve = User.objects.get(username='steve')

        # create another user manually, make him inactive
        woz = User.objects.create_user('woz', 'woz@apple.com', 'woz')
        woz.is_active = False
        woz.save()

        # list our users
        response = self.client.get(reverse('smartmin.user_list'))
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
        post_data['new_password'] = 'google'

        # need is active here or steve will be marked inactive
        post_data['is_active'] = '1'

        response = self.client.post(reverse('smartmin.user_update', args=[steve.id]), post_data, follow=True)
        self.assertEquals(200, response.status_code)
        self.assertTrue('form' not in response.context)

        # check that steve's group changed
        steve = User.objects.get(pk=steve.id)
        groups = steve.groups.all()
        self.assertEquals(1, len(groups))
        self.assertEquals(Group.objects.get(name='Editors'), groups[0])

        # assert steve can login with 'google' now
        self.assertTrue(self.client.login(username='steve', password='google'))

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

        self.author = User.objects.create_user('author', 'author@group.com', 'author')
        self.author.groups.add(Group.objects.get(name="Authors"))

        self.post = Post.objects.create(title="First Post", body="My First Post", tags="first", order=1,
                                        created_by=self.author, modified_by=self.author)

    def test_value_from_view(self):
        from smartmin.templatetags.smartmin import get_value_from_view

        context = dict(view=self.read_view, object=self.post)
        self.assertEquals(self.post.title, get_value_from_view(context, 'title'))
        self.assertEquals(self.post.created_on.strftime("%b %d, %Y %H:%M"), get_value_from_view(context, 'created_on'))

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
        
        





