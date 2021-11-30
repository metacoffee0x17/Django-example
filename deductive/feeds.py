from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed
from django.urls import reverse
from aldryn_newsblog.models import Article
from news_snippet.models import NewsSnippet

class LatestTVDataFeed(Feed):
    title = "Latest TV Data News"
    link = "/tv-data/"
    description = "Updates on changes and additions to tv data."

    def items(self):

        queryset = NewsSnippet.objects.all()
        queryset = queryset.order_by('-published_date')

        result = [ item for item in queryset if item.tag.name == "TV Data" ]
        return result

    def item_title(self, item):

        return item.title

    def item_description(self, item):
        return item.description

    def item_link(self, item):
        return item.link

class LatestAdvancedAdvertisingFeed(Feed):
    title = "Latest Advanced Advertising News"
    link = "/advanced-advertising/"
    description = "Updates on changes and additions to advanced advertising."

    def items(self):

        queryset = NewsSnippet.objects.all()
        queryset = queryset.order_by('-published_date')

        result = [ item for item in queryset if item.tag.name == "Advanced Advertising" ]
        return result

    def item_title(self, item):

        return item.title

    def item_description(self, item):
        return item.description

    def item_link(self, item):
        return item.link

class LatestConnectedCarFeed(Feed):
    title = "Latest Connected Car News"
    link = "/connected-car/"
    description = "Updates on changes and additions to connected car."

    def items(self):

        queryset = NewsSnippet.objects.all()
        queryset = queryset.order_by('-published_date')

        result = [ item for item in queryset if item.tag.name == "Connected Car" ]
        return result

    def item_title(self, item):

        return item.title

    def item_description(self, item):
        return item.description

    def item_link(self, item):
        return item.link


class AtomDativaArticleFeed(Feed):
    title = "Deductive Site Articles"
    link = "/"
    description = "Updates on changes and additions to article."
    feed_type = Atom1Feed

    def items(self):
        queryset = Article.objects.all()
        queryset = queryset.order_by('-publishing_date')
        return queryset[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.lead_in

    def item_categories(self, item):
        return item.tags.all()

    def item_author_name(self, item):
        return item.author

    def item_pubdate(self, item):
        return item.publishing_date
