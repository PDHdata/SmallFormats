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
COLORS = [
    _u('colorless',  ''),
    _u('white',      'W'),
    _u('blue',       'U'),
    _u('black',      'B'),
    _u('red',        'R'),
    _u('green',      'G'),
    _u('azorius',    'WU'),
    _u('dimir',      'UB'),
    _u('rakdos',     'BR'),
    _u('gruul',      'RG'),
    _u('selesnya',   'GW'),
    _u('orzhov',     'WB'),
    _u('izzet',      'UR'),
    _u('golgari',    'BG'),
    _u('boros',      'RW'),
    _u('simic',      'GU'),
    _u('esper',      'WUB'),
    _u('grixis',     'UBR'),
    _u('jund',       'BRG'),
    _u('naya',       'RGW'),
    _u('bant',       'GWU'),
    _u('abzan',      'WBG'),
    _u('jeskai',     'URW'),
    _u('sultai',     'BGU'),
    _u('mardu',      'RWB'),
    _u('temur',      'GUR'),
    _u('artifice',   'WUBR'),
    _u('chaos',      'UBRG'),
    _u('aggression', 'BRGW'),
    _u('altruism',   'RGWU'),
    _u('growth',     'GWUB'),
    _u('rainbow',    'WUBRG'),
]
