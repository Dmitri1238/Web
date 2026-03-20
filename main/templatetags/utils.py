# templatetags/utils.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, 0)

@register.filter
def to(value, arg):
    """Возвращает диапазон от value до arg (не включая)"""
    try:
        start = int(value)
        end = int(arg)
        return range(start, end)
    except (ValueError, TypeError):
        return []
    
@register.filter
def is_moderator(user):
    if user.is_authenticated:
        return user.groups.filter(name='Модератор').exists()
    return False

@register.filter
def sum_dict_values(d):
    if not isinstance(d, dict):
        return 0
    return sum(d.values())