from django.db import models
from djangocms_text_ckeditor.fields import HTMLField
from django.utils.translation import ugettext_lazy as _
from datetime import datetime
from django.utils.translation import ugettext
from django.db.models import Count
from filer.fields.image import FilerImageField
from djangocms_icon.fields import Icon

from cms.models.pluginmodel import CMSPlugin
from taggit.models import Tag

class PartnerTileModelPlugin(CMSPlugin):
    partner_name = models.CharField(
            max_length=255,
            verbose_name=_('partner name'),
            blank=False )
    partner_logo = FilerImageField(
        related_name=_('partner_logo_image'),
        null=False,
        blank=False
    )
    partner_summary = models.TextField(
        verbose_name=_('partner summary'),
        blank=False
    )
    partner_tags = models.CharField(
        max_length=255,
        blank=False
    )
    partner_icon = Icon()

    def get_instance(self, request):
        return { "partner_name": self.partner_name, 
                  "partner_logo": self.partner_logo, 
                  "partner_summary": self.partner_summary, 
                  "partner_tags": self.partner_tags.split(','),
                  "partner_icon": self.partner_icon }

    def __str__(self):
        return ugettext('partner : %(partner_name)s') % {
            'partner_name': self.partner_name,
        }