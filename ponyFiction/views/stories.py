# -*- coding: utf-8 -*-
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from ponyFiction.models import Story, CoAuthorsStory, Chapter, StoryView, Activity
from django.core.paginator import Paginator
from ponyFiction.forms.story import StoryForm
from ponyFiction.forms.comment import CommentForm
from django.core.exceptions import PermissionDenied

@csrf_protect
def story_view(request, story_id):
    story = get_object_or_404(Story, pk=story_id)
    chapters = story.chapter_set.order_by('order')
    comments_list = story.comment_set.all()
    paged = Paginator(comments_list, settings.COMMENTS_COUNT['page'], orphans=settings.COMMENTS_ORPHANS)
    num_pages = paged.num_pages
    comments = paged.page(1)
    page_title = story.title
    comment_form = CommentForm()
    if request.user.is_authenticated():
        activity = Activity.objects.get_or_create(author_id=request.user.id, story=story)[0]
        activity.last_views = story.views()
        activity.last_comments = comments_list.count()
        activity.last_vote_up = story.vote_up_count()
        activity.last_vote_down = story.vote_down_count()
        activity.save()
    data = {
       'story' : story,
       'comments' : comments,
       'chapters' : chapters,
       'num_pages' : num_pages,
       'page_title' : page_title,
       'comment_form': comment_form
       }
    # Если только одна глава
    if (story.chapter_set.count() == 1 and request.user.is_authenticated()):
        view = StoryView.objects.create()
        view.author = request.user
        view.story_id = story_id
        view.chapter = story.chapter_set.all()[0]
        view.save()
    return render(request, 'story_view.html', data)

@login_required
@csrf_protect
def story_work(request, story_id=False, edit=False, approve=False, publish=False, delete=False):
    if not story_id:
        return story_add(request, data={})
    story = get_object_or_404(Story, pk=story_id)
    if story.is_editable_by(request.user):
        if approve and request.user.is_staff:
            if story.approved:
                story.approved = False
            else:
                story.approved = True
            story.save(update_fields=['approved'])
            return redirect('author_dashboard')
        if delete:
            story.delete()
            return redirect('author_dashboard')
        if publish:
            if story.draft:
                story.draft = False
            else:
                story.draft = True
            story.save(update_fields=['draft'])
            return redirect('author_dashboard')
        if edit:
            return story_edit(request, story_id, data={})
    else:
        raise PermissionDenied

def story_add(request, data):
    if request.POST:
        form = StoryForm(request.POST)
        if form.is_valid():
            story = form.save()
            CoAuthorsStory.objects.create(
                story = story,
                author = request.user,
                approved = True,
            )
            return redirect('story_edit', story.id)
    else:
        form = StoryForm(initial={'finished': 0, 'freezed': 0, 'original': 1, 'rating': 4, 'size': 1})
        data['page_title'] = 'Новый рассказ'
        form.fields['button_submit'].initial = 'Добавить рассказ'
        
    data['form'] = form
    return render(request, 'story_work.html', data)

def story_edit(request, story_id, data):
    if request.POST:
        if (('button_submit' in request.POST) or ('button_save_draft' in request.POST)):
            form = StoryForm(request.POST, instance=Story.objects.get(pk=story_id))
            if form.is_valid():
                form.save()
                return redirect('story_edit', story_id)
        if 'button_delete' in request.POST:
            Story.objects.get(pk=story_id).delete()
            return redirect('author_dashboard')
    else:
        form = StoryForm(instance=Story.objects.get(pk=story_id))
        
    form.fields['button_submit'].initial = 'Сохранить изменения'
    chapters = Chapter.objects.filter(story=story_id).order_by('order')
    data.update({'form': form, 'story_edit': True, 'chapters': chapters, 'page_title' : u'Редактирование «%s»' % Story.objects.get(pk=story_id).title , 'story_id': story_id})
    return render(request, 'story_work.html', data)