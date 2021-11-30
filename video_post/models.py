from django.db import models
from djangocms_text_ckeditor.fields import HTMLField
from django.utils.translation import ugettext_lazy as _
from datetime import datetime
from django.utils.translation import ugettext
from django.db.models import Count

from cms.models.pluginmodel import CMSPlugin
from taggit.models import Tag
import array


class VideoPost(CMSPlugin):
    title = models.CharField(max_length=255)
    embedded_link = models.CharField(max_length=255)
    summary = HTMLField(
        verbose_name=_('summary'), default='',
        blank=True,
    )
    description = HTMLField(
        verbose_name=_('description'), default='',
        blank=True,
    )
    tag = models.CharField(max_length=255)
    published_date = models.DateTimeField(_('published date'))

    def __str__(self):
        return self.title

class ThumbVideoPostsPlugin(CMSPlugin):
    count_post = models.IntegerField(
        default=8,
        help_text=_('The maximum number of previous video posts to display.')
    )
    def get_posts(self, request):
        queryset = VideoPost.objects.all()
        queryset = queryset.order_by('-published_date')
        result = [x for x in queryset]
        return result[:self.count_post]

    def get_tags(self, request):
      
        query = """
            SELECT * FROM video_post_videopost GROUP BY tag"""
        raw_tags = list(VideoPost.objects.raw(query))
        tag_list = []
        for x in raw_tags:
            tags = x.tag.split(',')
            tag_list += tags
        return list(set(tag_list))
    
    def __str__(self):
        return ugettext('previous videos: %(count_post)s') % {
            'count_post': self.count_post,
        }