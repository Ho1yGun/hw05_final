import shutil
import tempfile
import time

from django import forms
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from yatube import settings
from yatube.settings import PAGINATOR_PAGE_LIST

from ..models import Follow, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.user2 = User.objects.create_user(username='follow_test_user')
        cls.user3 = User.objects.create_user(username='no_follow_test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.empty_group = Group.objects.create(
            title='Пустая группа для теста',
            slug='empty_group',
            description='посты в эту группу не должны попасть',
        )
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
        for i in range(18):
            cls.post = Post.objects.create(
                author=cls.user,
                text=f'Тестовый пост {i} где нужно больше 15ти знаков',
                group=cls.group,
                image=uploaded
            )
            time.sleep(0.001)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            'posts/index.html': reverse('posts:index'),
            'posts/group_list.html': reverse('posts:group_list',
                                             kwargs={'slug': self.group.slug}),
            'posts/profile.html': reverse(
                'posts:profile', kwargs={'username': self.user.username}),
            'posts/post_detail.html': reverse(
                'posts:post_detail', kwargs={'post_id': self.post.pk}),
            'posts/create_post.html': reverse('posts:post_create'),
            'core/404.html': reverse(
                'posts:group_list', kwargs={'slug': 'unexisting_page'}),
        }
        for template, reverse_name in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}))
        self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.asserts_text_username_group_title(first_object)

    def test_group_posts_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = (self.authorized_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group.slug})))
        first_object = response.context['page_obj'][0]
        self.asserts_text_username_group_title(first_object)
        additional_group_context = {
            first_object.group.slug: self.group.slug,
            first_object.group.description: self.group.description,
        }
        for context, expected_result in additional_group_context.items():
            with self.subTest(expected_result=expected_result):
                self.assertEqual(context, expected_result)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = (self.authorized_client.get(reverse(
            'posts:profile', kwargs={'username': self.user.username})))
        first_object = response.context['page_obj'][0]
        self.asserts_text_username_group_title(first_object)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = (self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.pk})))
        post_object = response.context['post']
        self.asserts_text_username_group_title(post_object)

    def test_post_create_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        post_create_form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in post_create_form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_detail_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = (self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.pk})))
        post_edit_form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in post_edit_form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_empty_group(self):
        """Все посты попали в нужную группу"""
        response = (self.authorized_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.empty_group.slug})))
        self.assertEqual(len(response.context['page_obj']), 0)

    def test_paginator(self):
        """Paginator работает исправно."""
        index_response = self.authorized_client.get(reverse('posts:index'))
        index_page_two = self.authorized_client.get(reverse('posts:index')
                                                    + '?page=2')
        group_response = (self.authorized_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group.slug})))
        group_page_two = (self.authorized_client.get(
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}) + '?page=2'))
        profile_response = (self.authorized_client.get(reverse(
            'posts:profile', kwargs={'username': self.user.username})))
        profile_page_two = (self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': self.user.username}) + '?page=2'))
        posts_per_page1 = PAGINATOR_PAGE_LIST
        posts_per_page2 = Post.objects.count() - PAGINATOR_PAGE_LIST
        cache.clear()
        tests_pages = {
            index_response: index_page_two,
            group_response: group_page_two,
            profile_response: profile_page_two,
        }
        for responses, page_two in tests_pages.items():
            padj_test_page1 = len(responses.context['page_obj'])
            padj_test_page2 = len(page_two.context['page_obj'])
            contexts_and_result = {
                padj_test_page1: posts_per_page1,
                padj_test_page2: posts_per_page2,
            }
            for context, expected_result in contexts_and_result.items():
                with self.subTest(expected_result=expected_result):
                    self.assertEqual(context, expected_result)

    def asserts_text_username_group_title(self, test_object):
        object_context = {
            test_object.pk: self.post.pk,
            test_object.text: self.post.text,
            test_object.author.pk: self.user.pk,
            test_object.author.username: self.user.username,
            test_object.group.pk: self.group.pk,
            test_object.group.title: self.group.title,
            test_object.image: self.post.image
        }
        for context, expected_result in object_context.items():
            with self.subTest(expected_result=expected_result):
                self.assertEqual(context, expected_result)

    def test_cache_page(self):
        """Кэш протестирован и работает как задумано"""
        test_cache_post = Post.objects.create(
            author=self.user,
            text='Это пост для тестирования кэша',
        )
        response = self.authorized_client.get(
            reverse('posts:index')).content
        test_cache_post.delete()
        response_cache = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertEqual(response, response_cache)
        cache.clear()
        response_clear = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertNotEqual(response, response_clear)

    def test_follow_add_and_delete(self):
        """Авторизованный пользователь может подписываться
         на других пользователей и удалять их из подписок."""
        self.authorized_client_new = Client()
        self.authorized_client_new.force_login(self.user2)
        follow_zero = Follow.objects.filter(author=self.user,
                                            user=self.user2).count()
        self.authorized_client_new.get(reverse(
            'posts:profile_follow', kwargs={'username': self.user.username}))
        current_follow = Follow.objects.filter(author=self.user,
                                               user=self.user2).count()
        self.assertEqual(current_follow, follow_zero + 1)
        self.authorized_client_new.get(reverse(
            'posts:profile_unfollow', kwargs={'username': self.user.username}))
        self.assertEqual(current_follow - 1, follow_zero)

    def test_new_posts_after_follow(self):
        """Новая запись пользователя появляется в ленте тех,
         кто на него подписан и не появляется в ленте тех, кто не подписан."""
        self.follower = Client()
        self.follower.force_login(self.user2)
        author_posts = Post.objects.filter(author=self.user).count()
        before_subscription = Post.objects.filter(
            author__following__user=self.user2).count()
        self.follower.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user.username}), follow=True)
        after_subscription = Post.objects.filter(
            author__following__user=self.user2).count()
        self.assertEqual(before_subscription + author_posts,
                         after_subscription)
        self.no_follower = Client()
        self.no_follower.force_login(self.user3)
        self.no_follower.get(reverse('posts:follow_index'))
        no_follow_posts = Post.objects.filter(
            author__following__user=self.user3).count()
        self.assertEqual(no_follow_posts, 0)
