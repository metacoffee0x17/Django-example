from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import ugettext_lazy as _

from .models import PartnerTileModelPlugin

@plugin_pool.register_plugin
class PartnerTilePlugin(CMSPluginBase):
    model = PartnerTileModelPlugin
    name = _("Partner Tile")
    render_template = "tile.html"
    cache = False

    def render(self, context, instance, placeholder):
        request = context.get('request')
        context['instance'] = instance
        context['tile'] = instance.get_instance(request)
        return context
