from django.conf.urls import url

from coffee_video.views import filter_by_tag
from coffee_video.views import get_content_by_id


urlpatterns = [
    url(r'^filter-by-tag', filter_by_tag, name="filter_by_tag"),
    url(r'^get-content-by-id', get_content_by_id, name="get_content_by_id"),
]
