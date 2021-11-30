from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import ugettext_lazy as _

from .models import CoffeeVideo, CoffeeVideoPluginModel

@plugin_pool.register_plugin
class LatestCoffeeeVideoPlugin(CMSPluginBase):
    model = CoffeeVideoPluginModel
    name = _("Latest Coffee Videos")
    render_template = "latest_video.html"
    cache = False

    def render(self, context, instance, placeholder):
        request = context.get('request')
        context['instance'] = instance
        context['video_posts'] = instance.get_posts(request)
        return context

@plugin_pool.register_plugin
class PreviousCoffeeVideoPlugin(CMSPluginBase):
    model = CoffeeVideoPluginModel
    name = _("Previous Coffee Videos")
    render_template = "previous_videos.html"
    cache = False

    def render(self, context, instance, placeholder):
        request = context.get('request')
        context['instance'] = instance
        context['video_posts'] = instance.get_posts(request)
        context['tag_list'] = instance.get_tags(request)
        print(context['tag_list'])
        return context
