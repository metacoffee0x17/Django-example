from django.db import models
from djangocms_text_ckeditor.fields import HTMLField
from django.utils.translation import ugettext_lazy as _
from datetime import datetime
from django.utils.translation import ugettext

from cms.models.pluginmodel import CMSPlugin
from taggit.models import Tag


class NewsSnippet(CMSPlugin):
    title = models.CharField(max_length=255)

    description = HTMLField(
        verbose_name=_('description'), default='',
        blank=True,
    )
    published_date = models.DateTimeField(_('published date'))
    tag = models.ForeignKey(
        Tag,
        null=True,
        blank=True,
        verbose_name=_('tag'),
        on_delete=models.CASCADE,
    )
    link = models.CharField(max_length=255)

    def __str__(self):
        return self.title

class NewsBlogLatestArticlesPlugin(CMSPlugin):
    latest_snippets = models.IntegerField(
        default=5,
        help_text=_('The maximum number of latest articles to display.')
    )
    news_tag = models.ForeignKey(
        Tag,
        null=True,
        blank=True,
        verbose_name=_('tag'),
        on_delete=models.CASCADE,
    )
    def get_snippets(self, request):
        queryset = NewsSnippet.objects.all()
        queryset = queryset.order_by('-published_date')
        result = [x for x in queryset if self.news_tag.name == x.tag.name ]
        return result[:self.latest_snippets]

    def __str__(self):
        return ugettext('latest snippets: %(latest_snippets)s') % {
            'latest_snippets': self.latest_snippets,
        }