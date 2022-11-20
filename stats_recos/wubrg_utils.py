def _c(color_str):
    "Convert a string like 'WUBRG' into a dict for urlpatterns"
    filter = {}
    for color in 'WUBRG':
        if color in color_str:
            filter[color.lower()] = True
    return filter

def _u(name, color_str):
    "Make a (name, num_colors, dict_colors) record"
    return (name, len(color_str), _c(color_str))

# powerset ahoy!
_COLORS_BASE = [
    ('colorless',  ''),
    ('white',      'W'),
    ('blue',       'U'),
    ('black',      'B'),
    ('red',        'R'),
    ('green',      'G'),
    ('azorius',    'WU'),
    ('dimir',      'UB'),
    ('rakdos',     'BR'),
    ('gruul',      'RG'),
    ('selesnya',   'GW'),
    ('orzhov',     'WB'),
    ('izzet',      'UR'),
    ('golgari',    'BG'),
    ('boros',      'RW'),
    ('simic',      'GU'),
    ('esper',      'WUB'),
    ('grixis',     'UBR'),
    ('jund',       'BRG'),
    ('naya',       'RGW'),
    ('bant',       'GWU'),
    ('abzan',      'WBG'),
    ('jeskai',     'URW'),
    ('sultai',     'BGU'),
    ('mardu',      'RWB'),
    ('temur',      'GUR'),
    ('artifice',   'WUBR'),
    ('chaos',      'UBRG'),
    ('aggression', 'BRGW'),
    ('altruism',   'RGWU'),
    ('growth',     'GWUB'),
    ('rainbow',    'WUBRG'),
]

_COLORS_MAP = dict(_COLORS_BASE)

COLORS = [_u(name, color_str) for name, color_str in _COLORS_BASE]

# these are not suitable for display, they're for looking up against
# because the color string needs to be alphabetized
REVERSE_COLORS = {"".join(sorted(color_str)): name for name, color_str in _COLORS_BASE}

def filter_to_name(filter):
    """Convert a dict to a color name.
    
    Examples:
      {W: True} => 'white'
      {W: True, U: True} => 'azorius'
      {W: True, U: False} => 'white'"""
    key = ""
    for letter in 'WUBRG':
        if letter in filter.keys() and filter[letter]:
            key += letter
    return REVERSE_COLORS["".join(sorted(key))]


def name_to_symbol(color_name):
    if color_name == 'colorless':
        return ('mana/C.svg',)
    return [f"mana/{c}.svg" for c in _COLORS_MAP[color_name]]


def identity_to_symbol(identity):
    return [f"mana/{c}.svg" for c in identity]
