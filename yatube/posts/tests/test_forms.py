import shutil
import tempfile


from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings, TestCase
from django.urls import reverse

from yatube import settings
from ..forms import PostForm
from ..models import Comment, Post

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост где нужно больше 15ти знаков',
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_new_post_created_in_database(self):
        """Создан новый пост в базе данных и произошел редирект"""
        posts_count = Post.objects.count()
        small_gif = (
             b'\x47\x49\x46\x38\x39\x61\x02\x00'
             b'\x01\x00\x80\x00\x00\x00\x00\x00'
             b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
             b'\x00\x00\x00\x2C\x00\x00\x00\x00'
             b'\x02\x00\x01\x00\x00\x02\x02\x0C'
             b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {'text': 'Второй пост для проверки добавления в базу',
                     'image': uploaded}
        response = self.authorized_client.post(
            reverse('posts:post_create'), data=form_data, follow=True)
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.post.author}))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(
            Post.objects.latest('id').text,
            form_data['text'],
        )
        self.assertEqual(
            Post.objects.latest('id').image,
            'posts/small.gif'
        )

    def test_change_post_in_database(self):
        """Новый пост успешно отредактирован"""
        change_post_data = {'text': 'измененный текст из формы'}
        self.authorized_client.post(reverse(
            'posts:post_edit', args=[self.post.pk]),
            data=change_post_data,
            follow=True,
        )
        self.assertTrue(
            Post.objects.filter(pk=self.post.pk,
                                text=change_post_data['text'])
        )

    def test_new_comment_created_in_database(self):
        """Создан новый комментарий в базе данных и произошел редирект
           Анонимный пользователь не может оставлять комментарии"""
        comments_count = Comment.objects.count()
        new_comment_form_data = {
            'post': self.post,
            'author': self.user,
            'text': 'коммент успешно добавлен'}
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=new_comment_form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.pk}))
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertEqual(
            Comment.objects.latest('id').text,
            new_comment_form_data['text'],
        )
        self.client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=new_comment_form_data,
            follow=True
        )
        self.assertEqual(
            Comment.objects.count(),
            comments_count + 1,
            'Анонимный пользователь может оставлять комментарии')

    def test_comment_created_in_database_guest_user(self):
        """комментировать посты может только авторизованный пользователь"""
        new_comment_form_data = {
            'post': self.post,
            'author': self.user,
            'text': 'коммент успешно добавлен'}
        response = self.client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=new_comment_form_data,
            follow=True
        )

