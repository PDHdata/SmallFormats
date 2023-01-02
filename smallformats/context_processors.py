from django.conf import settings
from django.urls import reverse_lazy

def sitename(request):
    return {
        'SITENAME': settings.SMALLFORMATS_NAME,
    }

_CARDS_LINKS = (
    ('Top cards', reverse_lazy('card-top')),
    ('Non-land cards', reverse_lazy('card-top-nonland')),
    ('Cards by color', reverse_lazy('card')),
)
_CMDRS_LINKS = (
    ('Top commanders', reverse_lazy('cmdr-top')),
    ('Commanders by color', reverse_lazy('cmdr')),
    ('Themes', reverse_lazy('theme')),
)
_LANDS_LINKS = (
    ('Top lands', reverse_lazy('land-top')),
    ('Lands by color', reverse_lazy('land')),
)
_LINKS = (
    # menu? title    link or menu items
    (True,  'Cards', _CARDS_LINKS),
    (True,  'Commanders', _CMDRS_LINKS),
    (True,  'Lands', _LANDS_LINKS),
)

def links(request):
    context = {
        'links': _LINKS,
    }

    if 'q' in request.GET:
        context['query'] = request.GET.get('q', '')

    return context
