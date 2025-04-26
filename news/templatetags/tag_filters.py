import re
from django import template

register = template.Library()

@register.filter
def clean_tags(tags):
    """
    Filter and return only tags that have no special symbols.
    """
    valid_tags = []
    for tag in tags:
        if re.match(r'^[a-zA-Z0-9\s]+$', tag.name) and  re.match(r'^[a-zA-Z0-9\s]+$', tag.slug):  # only letters, numbers, underscore, spaces
            valid_tags.append(tag)
    return valid_tags