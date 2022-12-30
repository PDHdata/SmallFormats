from django import template
from django.conf import settings
from stats_recos.wubrg_utils import identity_to_symbol, name_to_symbol, symbol_to_name

register = template.Library()


@register.filter()
def mana_symbols(identity):
    return "".join(
        [f'<img src="{settings.STATIC_URL}{sym}" class="mana-symbol">' for sym in identity_to_symbol(identity)]
    )

@register.filter()
def mana_symbols_by_name(name):
    try:
        return "".join(
            [f'<img src="{settings.STATIC_URL}{sym}" class="mana-symbol">' for sym in name_to_symbol(name)]
        )
    except KeyError:
        return ''


@register.filter()
def mana_symbol_to_name(symbol):
    try:
        return symbol_to_name(symbol)
    except IndexError:
        return ''
