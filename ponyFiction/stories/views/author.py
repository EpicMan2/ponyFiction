# -*- coding: utf-8 -*-
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from ponyFiction.stories.models import Author, Story, Comment, Vote, StoryView
from django.core.paginator import Paginator
from ponyFiction.stories.forms.author import AuthorEditEmailForm, AuthorEditPasswordForm, AuthorEditProfileForm 

@login_required
@csrf_protect
def author_info(request, user_id=None):
    data = {}
    if user_id is None:
        author = get_object_or_404(Author, pk=request.user.id)
        data['all_views'] = StoryView.objects.filter(story__authors=author).count()
        data['page_title'] = 'Мой кабинет'
        data['stories'] = author.story_set.all()
        template = 'author_dashboard.html'
    else:
        author = get_object_or_404(Author, pk=user_id)
        data['page_title'] = u'Автор: %s' % author.username
        data['stories'] = author.story_set.filter(draft=False, approved=True)
        template = 'author_overview.html'
    comments_list = author.comment_set.all()
    comments_count = comments_list.count()
    published_stories = Story.published.filter(authors=author).count()
    series = author.series_set.all()
    votes = [Vote.objects.filter(direction=True).filter(story__authors__id=author.id).count(),
             Vote.objects.filter(direction=False).filter(story__authors__id=author.id).count()]
    paged = Paginator(comments_list, settings.COMMENTS_COUNT['page'], orphans=settings.COMMENTS_ORPHANS)
    comments = paged.page(1).object_list
    num_pages = paged.num_pages
    data.update({
            'author' : author,
            'published_stories': published_stories,
            'series' : series,
            'comments' : comments,
            'num_pages': num_pages,
            'comments_count': comments_count,
            'votes': votes
            })
    return render(request, template, data)


@login_required
@csrf_protect
def author_edit(request):
    author = request.user
    data={}
    data['page_title'] = 'Настройки профиля'
    if request.POST:
        if 'save_profile' in request.POST:
            profile_form = AuthorEditProfileForm(request.POST, instance=author, prefix='profile_form')
            if profile_form.is_valid():
                profile_form.save()
                data['profile_ok'] = True            
        if 'save_email' in request.POST:
            email_form = AuthorEditEmailForm(request.POST, author=author, prefix='email_form')
            if email_form.is_valid():
                email_form.save()
                data['email_ok'] = True
        if 'save_password' in request.POST:
            password_form = AuthorEditPasswordForm(request.POST, author=author, prefix='password_form')
            if password_form.is_valid():
                password_form.save()
                data['password_ok'] = True
            else:
                data['password_form_nfe'] = password_form.non_field_errors()
    profile_form = AuthorEditProfileForm(instance=author, prefix='profile_form')
    email_form = AuthorEditEmailForm(author=author, prefix='email_form')
    password_form = AuthorEditPasswordForm(author=author, prefix='password_form')
    data.update({'profile_form': profile_form, 'email_form': email_form, 'password_form': password_form})
    return render(request, 'author_profile_edit.html', data)