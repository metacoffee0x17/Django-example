from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import ugettext_lazy as _

from .models import CaseStudiesTilePluginModel

@plugin_pool.register_plugin
class CaseStudiesTilePlugin(CMSPluginBase):
    model = CaseStudiesTilePluginModel
    name = _("Case Studies Tile")
    render_template = "case_studies_tile.html"
    cache = False

    def render(self, context, instance, placeholder):
        request = context.get('request')
        context['instance'] = instance
        context['tile'] = instance.get_instance(request)
        print(context['tile']['download_file'])
        return context
