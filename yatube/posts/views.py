from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Comment, Follow, Group, Post, User
from .utils import paginator_page_obj


def index(request):
    post_list = Post.objects.all().order_by('-pub_date')
    page_obj = paginator_page_obj(request, post_list)
    template = 'posts/index.html'
    title = "Последние обновления на сайте"
    context = {
        'title': title,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def group_posts(request, slug):
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    post_list = Post.objects.filter(group=group).order_by('-pub_date')
    page_obj = paginator_page_obj(request, post_list)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    template = 'posts/profile.html'
    user = get_object_or_404(User, username=username)
    post_list = Post.objects.filter(author=user).order_by('-pub_date')
    page_obj = paginator_page_obj(request, post_list)
    context = {
        'page_obj': page_obj,
        'author': user,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'posts/post_detail.html'
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    comments = Comment.objects.filter(post=post)
    context = {
        'post': post,
        'form': form,
        'comments': comments,
    }
    return render(request, template, context)


@login_required
def post_create(request):
    template = 'posts/create_post.html'
    form = PostForm(request.POST or None, files=request.FILES or None,)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', username=post.author)
    context = {
        'form': form,
    }
    return render(request, template, context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    template = 'posts/create_post.html'
    if request.user != post.author:
        return redirect('posts:post_detail', post_id=post_id)
    form = PostForm(request.POST or None,
                    files=request.FILES or None,
                    instance=post,)
    is_edit = True
    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect('posts:post_detail', post_id=post_id)
    context = {
        'form': form,
        'is_edit': is_edit,
        'post': post,
    }
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user)
    template = 'posts/follow.html'
    page_obj = paginator_page_obj(request, post_list)
    context = {
        'page_obj': page_obj
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    if username != request.user.username:
        Follow.objects.create(user=request.user,
                              author=User.objects.get(username=username))
        return redirect('posts:follow_index')
    return redirect('posts:index')


@login_required
def profile_unfollow(request, username):
    # Дизлайк, отписка
    Follow.objects.filter(user=request.user,
                          author=User.objects.get(username=username)
                          ).delete()
    return redirect('posts:follow_index')
