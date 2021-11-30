from django import template

register = template.Library()

@register.filter
def pass_script(value):
    return value.replace("&lt;","<").replace("&gt;", ">")