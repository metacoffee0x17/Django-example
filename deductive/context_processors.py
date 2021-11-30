from django.core.cache import cache
from page_setting.models import Page_Tag
from cms.models.pagemodel import Page
from django.conf import settings


def extended_page_options(request):
	cls = Page_Tag
	page_tag = None
	try:
		current_node_id = request.current_page.node_id
		page_ids = Page.objects.filter(node_id=current_node_id).filter(publisher_is_draft=1).values('id')
		page_tag = Page_Tag.objects.get(page_id=page_ids[0]['id'])
	except:
		return {
			'PAGE_TAG': None,
			'MAILCHIMP_INTEREST': settings.MAILCHIMP_INTEREST,
			'FREEBIE_CHOICES': settings.FREEBIE_CHOICES,
			'SITEURL':  request.get_full_path(),
			'RECAPTCHA_SITE_KEY': settings.RECAPTCHA_SITE_KEY
		}
	return {
		'PAGE_TAG': page_tag.page_tag,
		'MAILCHIMP_INTEREST': settings.MAILCHIMP_INTEREST,
		'FREEBIE_CHOICES': settings.FREEBIE_CHOICES,
		'SITEURL':  request.get_full_path(),
		'RECAPTCHA_SITE_KEY': settings.RECAPTCHA_SITE_KEY
	}
