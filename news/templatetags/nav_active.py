from django import template
from django.urls import resolve
from django.urls.exceptions import Resolver404

register = template.Library()

@register.simple_tag(takes_context=True)
def active(context, pattern_or_urlname, css_class='active'):
    """
    Returns the given CSS class if the current URL path matches the given pattern or URL name.
    
    Usage:
    {% load active_link_tags %}
    <a href="{% url 'home' %}" class="{% active 'home' %}">Home</a>
    <a href="{% url 'about' %}" class="{% active 'about' %}">About</a>
    
    With custom CSS class:
    <a href="{% url 'home' %}" class="nav-link {% active 'home' 'bg-primary text-white' %}">Home</a>
    """
    try:
        request = context['request']
        current_path = request.path
        
        # Check if pattern_or_urlname is a URL pattern or name
        if pattern_or_urlname.startswith('/'):
            # It's a URL pattern
            if current_path == pattern_or_urlname:
                return css_class
        else:
            # It's a URL name, try to resolve it
            try:
                current_url_name = resolve(current_path).url_name
                if current_url_name == pattern_or_urlname:
                    return css_class
            except Resolver404:
                return ''
    except (KeyError, AttributeError):
        # If request is not in context or doesn't have path attribute
        return ''
    
    return ''
