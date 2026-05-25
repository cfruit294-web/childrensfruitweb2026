from django import template
from django.urls import reverse

register = template.Library()


@register.filter
def user_color(username):
    palette = ['#00913a','#e07b00','#1565c0','#7b1fa2','#b71c1c','#006064','#2e7d32','#e65100','#4527a0','#37474f']
    h = sum(ord(c) * (i * 7 + 3) for i, c in enumerate(str(username)[:12])) % len(palette)
    return palette[h]


@register.filter
def user_initials(display_name):
    parts = str(display_name or '').strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    s = str(display_name or '?')
    return s[:2].upper() if len(s) >= 2 else (s[0].upper() if s else '?')


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
