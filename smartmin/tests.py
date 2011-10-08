from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Group
from blog.models import Post

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

        self.post = Post.objects.create(title="Test Post", body="This is the body of my first test post", tags="testing",
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

    def test_create(self):
        self.client.login(username='author', password='author')
        
        post_data = dict(title="New Post", body="This is a new post", tags="post")
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
        
        post_data = dict(title="New Post", body="This is a new post", tags="post")
        response = self.client.post(reverse('blog.post_create'), post_data, follow=True)

        post = list(Post.objects.all())[-1]

        self.assertEquals(200, response.status_code)
        self.assertContains(response, "Your new post has been saved.")

        post_data = dict(title="New Post", body="Updated post content", tags="post")
        response = self.client.post(reverse('blog.post_update', args=[post.id]), post_data, follow=True)

        self.assertEquals(200, response.status_code)
        self.assertContains(response, "Your blog post has been updated.")
        
        
        


