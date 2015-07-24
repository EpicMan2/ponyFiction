# -*- coding: utf-8 -*-
from cacheops import invalidate_obj
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.datetime_safe import datetime
from django.views.decorators.csrf import csrf_protect
from json import dumps
from django.views.decorators.http import require_POST
from ponyFiction.models import Author, Story, Favorites, Bookmark, StoryEditLogItem
from ponyFiction.ajax.decorators import ajax_required
from ponyFiction.views.story import StoryDelete, _story_vote
from django.utils.decorators import method_decorator
  
@login_required
@csrf_protect
def story_publish_warning_ajax(request, story_id):
    story = get_object_or_404(Story, pk=story_id)
    if (story.editable_by(request.user) or request.user.is_staff):
        data = {
            'page_title' : 'Неудачная попытка публикации',
            'story' : story,
            'need_words': settings.PUBLISH_SIZE_LIMIT
        }
        return render(request, 'includes/ajax/story_ajax_publish_warning.html', data)
    else:
        raise PermissionDenied


@ajax_required    
@login_required
@csrf_protect
@require_POST
def story_publish_ajax(request, story_id):
    """ Публикация рассказа по AJAX """
    story = get_object_or_404(Story, pk=story_id)
    if (story.editable_by(request.user) or request.user.is_staff):
        if (story.publishable or (not story.draft and not story.publishable)):
            if story.draft:
                story.draft = False
            else:
                story.draft = True
            StoryEditLogItem.create(
                action = StoryEditLogItem.Actions.Unpublish if story.draft else StoryEditLogItem.Actions.Publish,
                user = request.user,
                story = story,
            )
            story.save(update_fields=['draft', 'approved'])
            return HttpResponse(story_id)
        else:
            return story_publish_warning_ajax(request, story_id)
    else:
        raise PermissionDenied


@ajax_required
@login_required
@csrf_protect
@require_POST
def story_approve_ajax(request, story_id):
    """ Одобрение рассказа по AJAX """

    if request.user.is_staff:
        story = get_object_or_404(Story, pk=story_id)
        if story.approved:
            story.approved = False
        else:
            story.date = datetime.now()
            story.approved = True
        StoryEditLogItem.create(
            action = StoryEditLogItem.Actions.Approve if story.approved else StoryEditLogItem.Actions.Unapprove,
            user = request.user,
            story = story,
        )
        story.save(update_fields=['approved', 'date'])
        return HttpResponse(story_id)
    else:
        raise PermissionDenied


@ajax_required
@login_required
@csrf_protect
@require_POST
def story_bookmark_ajax(request, story_id):
    """ Добавление рассказа в закладки """
    
    story = get_object_or_404(Story.objects.accessible(user=request.user), pk=story_id)
    (bookmark, created) = Bookmark.objects.get_or_create(story=story, author=request.user)
    if not created:
        bookmark.delete()
    invalidate_obj(story)
    return HttpResponse(story_id)


@ajax_required
@login_required
@csrf_protect
@require_POST
def story_favorite_ajax(request, story_id):
    """ Добавление рассказа в избранное """

    story = get_object_or_404(Story.objects.accessible(user=request.user), pk=story_id)
    (favorite, created) = Favorites.objects.get_or_create(story=story, author=request.user)
    if not created:
        favorite.delete()
    invalidate_obj(story)
    return HttpResponse(story_id)

@ajax_required
@login_required
@csrf_protect
@require_POST
def story_vote_ajax(request, story_id, direction):
    direction = True if (direction == 'plus') else False
    story = _story_vote(request, story_id, direction)
    return HttpResponse(dumps([0, 0]))


class AjaxStoryDelete(StoryDelete):
    
    template_name = 'includes/ajax/story_ajax_confirm_delete.html'
    
    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        return StoryDelete.dispatch(self, request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        parent_response = super(AjaxStoryDelete, self).delete(self, request, *args, **kwargs)
        if parent_response.status_code == 302:
            return HttpResponse(self.story_id)
        else:
            return parent_response
