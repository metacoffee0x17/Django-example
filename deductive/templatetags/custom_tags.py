from django import template
import re

register = template.Library()

@register.filter
def split(value, arg):
    return value.split(arg)
@register.filter
def remove_img(value):
    regex = re.compile("<img[^>]*>")
    value = re.sub(regex, "", value)
    return value
