from django import template
from django.conf import settings
from stats_recos.wubrg_utils import identity_to_symbol, name_to_symbol

register = template.Library()


@register.filter()
def mana_symbols(identity):
    return "".join(
        [f'<img src="{settings.STATIC_URL}{sym}" class="mana-symbol">' for sym in identity_to_symbol(identity)]
    )

@register.filter()
def mana_symbols_by_name(name):
    if name == 'top': return ''
    return "".join(
        [f'<img src="{settings.STATIC_URL}{sym}" class="mana-symbol">' for sym in name_to_symbol(name)]
    )
