from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import ugettext_lazy as _

from .models import NewsSnippet, NewsBlogLatestArticlesPlugin

@plugin_pool.register_plugin
class NewsSnippetPligin(CMSPluginBase):
    model = NewsBlogLatestArticlesPlugin
    name = _("Latest News Snippets")
    render_template = "news_snippet.html"
    cache = False

    def render(self, context, instance, placeholder):
        request = context.get('request')
        context['instance'] = instance
        context['snippet_list'] = instance.get_snippets(request)
        return context
