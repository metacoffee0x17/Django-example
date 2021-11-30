from django.db import models
from djangocms_text_ckeditor.fields import HTMLField
from django.utils.translation import ugettext_lazy as _
from datetime import datetime
from django.utils.translation import ugettext
from django.db.models import Count
from filer.fields.image import FilerImageField
from djangocms_icon.fields import Icon
from filer.fields.file import FilerFileField

from cms.models.pluginmodel import CMSPlugin
from taggit.models import Tag

class CaseStudiesTilePluginModel(CMSPlugin):
    tile_name = models.CharField(
            max_length=255,
            verbose_name=_('tile name'),
            blank=False )
    tile_summary = models.CharField(
        max_length=255,
        verbose_name=_('tile summary'),
        blank=False
    )
    detail_link = models.SlugField(
            verbose_name=_('deatil slug'),
            max_length=255,
            db_index=True,
            blank=True,
        )
    tile_icon = FilerImageField(
        related_name=_('tile_icon_image'),
        null=False,
        blank=False
    )
    download_file = FilerFileField(
        verbose_name=_('File'),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )

    def get_instance(self, request):
        return { "tile_name": self.tile_name, 
                  "tile_summary": self.tile_summary,
                  "detail_link": self.detail_link,
                  "tile_icon": self.tile_icon,
                  "download_file": self.download_file,
                }

    def __str__(self):
        return ugettext('case studies -  : %(tile_name)s') % {
            'tile_name': self.tile_name,
        }