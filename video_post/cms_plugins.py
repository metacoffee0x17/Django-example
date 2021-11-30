from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import ugettext_lazy as _

from .models import VideoPost, ThumbVideoPostsPlugin

@plugin_pool.register_plugin
class ThumbListVideoPlugin(CMSPluginBase):
    model = ThumbVideoPostsPlugin
    name = _("Video Library")
    render_template = "thumb_list_videos.html"
    cache = False

    def render(self, context, instance, placeholder):
        request = context.get('request')
        context['instance'] = instance
        context['video_posts'] = instance.get_posts(request)
        context['tag_list'] = instance.get_tags(request)
        print(context['tag_list'])
        return context
