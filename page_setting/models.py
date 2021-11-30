from django.db import models
from django.utils.translation import ugettext_lazy as _
from cms.models.pagemodel import Page

class Page_Tag(models.Model):
    page = models.OneToOneField(Page, unique=True, verbose_name=_("Page"),
        editable=False, related_name='extended_fields')
    page_tag = models.CharField(max_length = 255)
