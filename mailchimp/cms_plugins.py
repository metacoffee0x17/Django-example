from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from cms.models.pluginmodel import CMSPlugin
from django.utils.translation import ugettext_lazy as _

@plugin_pool.register_plugin
class MailChimp(CMSPluginBase):
    model = CMSPlugin
    render_template = "mailchimp.html"
    cache = False


@plugin_pool.register_plugin
class ContactFrom(CMSPluginBase):
    model = CMSPlugin
    render_template = "contact_form.html"
    cache = False