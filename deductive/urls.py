# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

from cms.sitemaps import CMSSitemap
from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.static import serve
from django.http import HttpResponse
from deductive.feeds import (LatestAdvancedAdvertisingFeed, LatestConnectedCarFeed, LatestTVDataFeed, AtomDativaArticleFeed)

admin.autodiscover()

urlpatterns = [
    url(r'^sitemap\.xml$', sitemap,
        {'sitemaps': {'cmspages': CMSSitemap}}),
]

urlpatterns += [
    url(r'^robots.txt', lambda r: HttpResponse("User-agent: *\nDisallow: /search", content_type="text/plain")),
    url(r'^feeds/all.atom.xml/', AtomDativaArticleFeed()),
    url(r'^feeds/atom.xml/', AtomDativaArticleFeed()),
    url(r'^admin/', admin.site.urls),  # NOQA
    url(r'^coffee-video/', include('coffee_video.urls')),
    url(r'^video-post/', include('video_post.urls')),
    url(r'^', include('cms.urls')),
    url(r'^search/', include('haystack.urls')),
    url(r'^advanced-advertising/rss-feed', LatestAdvancedAdvertisingFeed()),
    url(r'^tv-data/rss-feed', LatestTVDataFeed()),
    url(r'^connected-car/rss-feed', LatestConnectedCarFeed()),
]

# This is only needed when using runserver.
if settings.DEBUG:
    urlpatterns = [
        url(r'^media/(?P<path>.*)$', serve,
            {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
        ] + staticfiles_urlpatterns() + urlpatterns
# if settings.DEBUG:
#     urlpatterns = [
#     url(r'^media/(?P<path>.*)$', 'django.views.static.serve',
#         {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
#     url(r'', include('django.contrib.staticfiles.urls')),
# ] + urlpatterns
