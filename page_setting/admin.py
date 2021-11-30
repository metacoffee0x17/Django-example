from page_setting.models import Page_Tag
from cms.admin.pageadmin import PageAdmin
from cms.models.pagemodel import Page
from django.contrib import admin

class Page_TagAdmin(admin.TabularInline):
    model = Page_Tag
    
PageAdmin.inlines.append(Page_TagAdmin)

admin.site.unregister(Page)
admin.site.register(Page, PageAdmin)