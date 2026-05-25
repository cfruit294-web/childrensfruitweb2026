from django import template
from django.urls import reverse

register = template.Library()


@register.filter
def is_partner(user):
    return user.is_authenticated and user.role == 'partner'


@register.filter
def is_volunteer(user):
    return user.is_authenticated and user.role == 'volunteer'


@register.filter
def is_member(user):
    return user.is_authenticated and user.role == 'member'


@register.simple_tag
def dashboard_url(user):
    if not user.is_authenticated:
        return reverse('login')
    role_map = {
        'partner': 'partner_dashboard',
        'volunteer': 'volunteer_dashboard',
        'member': 'visitor_dashboard',
        'visitor': 'visitor_dashboard',
    }
    return reverse(role_map.get(user.role, 'visitor_dashboard'))
