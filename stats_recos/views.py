from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseNotAllowed
from django.urls import reverse_lazy
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from decklist.models import Card, Deck, Printing, CardInDeck, SiteStat
from .wubrg_utils import COLORS, filter_to_name, name_to_symbol
from django_htmx.http import trigger_client_event, HttpResponseClientRefresh
import operator
import functools


_CARDS_LINKS = (
    ('Top cards', reverse_lazy('card-top')),
    ('Cards by color', reverse_lazy('card')),
 )
_CMDRS_LINKS = (
    ('Top commanders', reverse_lazy('cmdr-top')),
    ('Commanders by color', reverse_lazy('cmdr')),
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
    (False, 'Partner decks', reverse_lazy('partner-decks')),
)

def _deck_count_exact_color(w, u, b, r, g):
    return (
        CardInDeck.objects
        .filter(
            deck__pdh_legal=True,
            is_pdh_commander=True,
        )
        .aggregate(count=(
            Count('deck',
            filter=
                Q(card__identity_w=w) & 
                Q(card__identity_u=u) &
                Q(card__identity_b=b) &
                Q(card__identity_r=r) &
                Q(card__identity_g=g),
            distinct=True,
            ))
        )
    )['count']


def _deck_count_at_least_color(w, u, b, r, g):
    if not any([w, u, b, r, g]):
        return Deck.objects.count()

    # build up a filter for the aggregation
    # that has a Q object set to True for each color we
    # care about and nothing for the colors which we don't
    q_objs = []
    for c in 'wubrg':
        if locals()[c]:
            key = f'card__identity_{c}'
            q_objs.append(Q(**dict([(key,True),])))
    filter_q = functools.reduce(operator.and_, q_objs)

    return (
        CardInDeck.objects
        .filter(
            deck__pdh_legal=True,
            is_pdh_commander=True,
        )
        .aggregate(count=Count('deck', filter=filter_q, distinct=True))
    )['count']


@functools.cache
def _get_face_card():
    top_cmdr = (
        Card.objects
        .filter(
            deck_list__deck__pdh_legal=True,
            deck_list__is_pdh_commander=True,
        )
        .annotate(num_decks=Count('deck_list'))
        .order_by('-num_decks')
        .first()
    )
    if top_cmdr and top_cmdr.default_printing:
        return top_cmdr.name, top_cmdr.default_printing.image_uri

    # this only happens if we have no cards/printings in the database
    return "Command Tower", "https://cards.scryfall.io/normal/front/b/f/bf5dafb0-4fb1-470d-85ce-88f3ae32340b.jpg?1568580226"


def stats_index(request, page="stats/index.html"):
    name, image_uri = _get_face_card()
    try:
        stats = SiteStat.objects.latest()
    except SiteStat.DoesNotExist:
        stats = None

    return render(
        request,
        page,
        context={
            'links': _LINKS,
            'image_uri': image_uri,
            'face_card_name': name,
            'stats': stats,
        },
    )


def partner_decks(request):
    partner_decks = (
        Deck.objects
        .filter(pdh_legal=True)
        .annotate(num_cmdrs=Count(
            'card_list', filter=Q(card_list__is_pdh_commander=True)
        ))
        .filter(num_cmdrs__gt=1)
    )
    paginator = Paginator(partner_decks, 25, orphans=3)
    page_number = request.GET.get('page')
    decks_page = paginator.get_page(page_number)

    return render(
        request,
        "stats/partner_decks.html",
        context={
            'decks': decks_page,
            'links': _LINKS,
        },
    )


def commander_index(request):
    colors = [
        [(c[0], name_to_symbol(c[0]), f'cmdr-{c[0]}') for c in COLORS if c[1] == 0],
        [(c[0], name_to_symbol(c[0]), f'cmdr-{c[0]}') for c in COLORS if c[1] == 1],
        [(c[0], name_to_symbol(c[0]), f'cmdr-{c[0]}') for c in COLORS if c[1] == 2],
        [(c[0], name_to_symbol(c[0]), f'cmdr-{c[0]}') for c in COLORS if c[1] == 3],
        [(c[0], name_to_symbol(c[0]), f'cmdr-{c[0]}') for c in COLORS if c[1] == 4],
        [(c[0], name_to_symbol(c[0]), f'cmdr-{c[0]}') for c in COLORS if c[1] == 5],
    ]
    return render(
        request,
        "stats/commander_index.html",
        context={
            'colors': colors,
            'links': _LINKS,
        },
    )


def top_commanders(request):
    cmdr_cards = (
        Card.objects
        .filter(
            deck_list__deck__pdh_legal=True,
            deck_list__is_pdh_commander=True,
        )
        .annotate(num_decks=Count('deck_list'))
        .order_by('-num_decks')
    )
    deck_count = Deck.objects.filter(pdh_legal=True).count()
    paginator = Paginator(cmdr_cards, 25, orphans=3)
    page_number = request.GET.get('page')
    cards_page = paginator.get_page(page_number)

    return render(
        request,
        "stats/commanders.html",
        context={
            'heading': 'top',
            'cards': cards_page,
            'deck_count': deck_count,
            'links': _LINKS,
        },
    )


def commanders_by_color(request, w=False, u=False, b=False, r=False, g=False):
    cmdrs = (
        Card.objects
        .prefetch_related('printings')
        .filter(
            identity_w=w,
            identity_u=u,
            identity_b=b,
            identity_r=r,
            identity_g=g,
        )
        .filter(
            # TODO: banlist? silver cards which say "Summon"?
            # TODO: backgrounds
            type_line__contains='Creature',
            printings__rarity=Printing.Rarity.UNCOMMON,
        )
        .annotate(num_decks=Count(
            'deck_list',
            distinct=True,
            filter=Q(deck_list__is_pdh_commander=True) & 
                   Q(deck_list__deck__pdh_legal=True)
        ))
        .filter(num_decks__gt=0)
        .order_by('-num_decks')
    )
    paginator = Paginator(cmdrs, 25, orphans=3)
    page_number = request.GET.get('page')
    cards_page = paginator.get_page(page_number)

    return render(
        request,
        "stats/commanders.html",
        context={
            'heading': filter_to_name({'W':w,'U':u,'B':b,'R':r,'G':g}),
            'cards': cards_page,
            # TODO: probably fails to account for partners
            'deck_count': _deck_count_exact_color(w, u, b, r, g),
            'links': _LINKS,
        },
    )


def land_index(request):
    colors = [
        [(c[0], name_to_symbol(c[0]), f'land-{c[0]}') for c in COLORS if c[1] == 0],
        [(c[0], name_to_symbol(c[0]), f'land-{c[0]}') for c in COLORS if c[1] == 1],
        [(c[0], name_to_symbol(c[0]), f'land-{c[0]}') for c in COLORS if c[1] == 2],
        [(c[0], name_to_symbol(c[0]), f'land-{c[0]}') for c in COLORS if c[1] == 3],
        [(c[0], name_to_symbol(c[0]), f'land-{c[0]}') for c in COLORS if c[1] == 4],
        [(c[0], name_to_symbol(c[0]), f'land-{c[0]}') for c in COLORS if c[1] == 5],
    ]
    return render(
        request,
        "stats/land_index.html",
        context={
            'colors': colors,
            'links': _LINKS,
        },
    )


def top_lands(request):
    land_cards = (
        Card.objects
        .filter(
            deck_list__deck__pdh_legal=True,
            type_line__contains='Land',
        )
        .annotate(num_decks=Count('deck_list'))
        .order_by('-num_decks')
        .filter(num_decks__gt=0)
    )
    deck_count = Deck.objects.filter(pdh_legal=True).count()
    paginator = Paginator(land_cards, 25, orphans=3)
    page_number = request.GET.get('page')
    cards_page = paginator.get_page(page_number)

    return render(
        request,
        "stats/lands.html",
        context={
            'heading': 'top',
            'cards': cards_page,
            'deck_count': deck_count,
            'links': _LINKS,
        },
    )


def lands_by_color(request, w=False, u=False, b=False, r=False, g=False):
    land_cards = (
        Card.objects
        .filter(
            type_line__contains='Land',
            identity_w=w,
            identity_u=u,
            identity_b=b,
            identity_r=r,
            identity_g=g,
        )
        .annotate(num_decks=Count(
            'deck_list',
            distinct=True,
            filter=Q(deck_list__deck__pdh_legal=True),
        ))
        .order_by('-num_decks')
        .filter(num_decks__gt=0)
    )
    paginator = Paginator(land_cards, 25, orphans=3)
    page_number = request.GET.get('page')
    cards_page = paginator.get_page(page_number)

    return render(
        request,
        "stats/lands.html",
        context={
            'heading': filter_to_name({'W':w,'U':u,'B':b,'R':r,'G':g}),
            'cards': cards_page,
            'deck_count': _deck_count_at_least_color(w, u, b, r, g),
            'links': _LINKS,
        },
    )


def card_index(request):
    colors = [
        [(c[0], name_to_symbol(c[0]), f'card-{c[0]}') for c in COLORS if c[1] == 0],
        [(c[0], name_to_symbol(c[0]), f'card-{c[0]}') for c in COLORS if c[1] == 1],
        [(c[0], name_to_symbol(c[0]), f'card-{c[0]}') for c in COLORS if c[1] == 2],
        [(c[0], name_to_symbol(c[0]), f'card-{c[0]}') for c in COLORS if c[1] == 3],
        [(c[0], name_to_symbol(c[0]), f'card-{c[0]}') for c in COLORS if c[1] == 4],
        [(c[0], name_to_symbol(c[0]), f'card-{c[0]}') for c in COLORS if c[1] == 5],
    ]
    return render(
        request,
        "stats/card_index.html",
        context={
            'colors': colors,
            'links': _LINKS,
        },
    )


def top_cards(request):
    cards = (
        Card.objects
        .filter(
            deck_list__deck__pdh_legal=True,
        )
        .annotate(num_decks=Count('deck_list'))
        .filter(num_decks__gt=0)
        .order_by('-num_decks')
    )
    deck_count = Deck.objects.filter(pdh_legal=True).count()
    paginator = Paginator(cards, 25, orphans=3)
    page_number = request.GET.get('page')
    cards_page = paginator.get_page(page_number)

    return render(
        request,
        "stats/cards.html",
        context={
            'heading': 'top',
            'cards': cards_page,
            'deck_count': deck_count,
            'links': _LINKS,
        },
    )


def cards_by_color(request, w=False, u=False, b=False, r=False, g=False):
    cards = (
        Card.objects
        .filter(
            identity_w=w,
            identity_u=u,
            identity_b=b,
            identity_r=r,
            identity_g=g,
        )
        .annotate(num_decks=Count(
            'deck_list',
            distinct=True,
            filter=Q(deck_list__deck__pdh_legal=True),
        ))
        .order_by('-num_decks')
        .filter(num_decks__gt=0)
    )
    paginator = Paginator(cards, 25, orphans=3)
    page_number = request.GET.get('page')
    cards_page = paginator.get_page(page_number)

    return render(
        request,
        "stats/cards.html",
        context={
            'heading': filter_to_name({'W':w,'U':u,'B':b,'R':r,'G':g}),
            'cards': cards_page,
            'deck_count': _deck_count_at_least_color(w, u, b, r, g),
            'links': _LINKS,
        },
    )


def single_card(request, card_id):
    card = get_object_or_404(Card, pk=card_id)

    could_be_in = _deck_count_at_least_color(
        card.identity_w,
        card.identity_u,
        card.identity_b,
        card.identity_r,
        card.identity_g
    )

    is_in = (
        Deck.objects
        .filter(
            pdh_legal=True,
            card_list__card=card,
        )
    )

    commands = (
        Deck.objects
        .filter(
            pdh_legal=True,
            card_list__card=card,
            card_list__is_pdh_commander=True,
        )
    )

    cmdrs = (
        CardInDeck.objects
        .filter(
            is_pdh_commander=True,
            deck__in=(
                Deck.objects
                .filter(
                    pdh_legal=True,
                    card_list__card=card,
                )
                .distinct()
            ),
        )
        .exclude(is_pdh_commander=True, card=card)
        .values('card')
        .annotate(count=Count('deck'))
        .values('count', 'card__id', 'card__name')
        .order_by('-count')
    )
    paginator = Paginator(cmdrs, 25, orphans=3)
    page_number = request.GET.get('page')
    cmdrs_page = paginator.get_page(page_number)

    return render(
        request,
        "stats/single_card.html",
        context={
            'card': card,
            'is_in': is_in.count(),
            'commands': commands.count(),
            'could_be_in': could_be_in,
            'commanders': cmdrs_page,
            'links': _LINKS,
        },
    )


def single_cmdr(request, card_id):
    card = get_object_or_404(Card, pk=card_id)

    could_be_in = _deck_count_at_least_color(
        card.identity_w,
        card.identity_u,
        card.identity_b,
        card.identity_r,
        card.identity_g
    )

    commands = (
        Deck.objects
        .filter(
            pdh_legal=True,
            card_list__card=card,
            card_list__is_pdh_commander=True,
        )
        .order_by('-updated_time')
    )

    context = {}
    # card type codes, see `hx_common_cards`
    for letter in 'caeisplg':
        if page_number := request.GET.get(letter, default=None):
            try:
                if int(page_number) > 1:
                    context[f'page_{letter}'] = page_number
            except ValueError:
                # user probably munged the URL with something like "?c=foo"
                pass
    
    context.update({
        'card': card,
        'commands': commands.count(),
        'top_decks': commands[:4],
        'could_be_in': could_be_in,
        'links': _LINKS,
    })

    return render(
        request,
        "stats/single_cmdr.html",
        context=context,
    )


def single_cmdr_decklist(request, card_id):
    card = get_object_or_404(Card, pk=card_id)

    commands = (
        Deck.objects
        .filter(
            pdh_legal=True,
            card_list__card=card,
            card_list__is_pdh_commander=True,
        )
        .order_by('-updated_time')
    )
    paginator = Paginator(commands, 20, orphans=3)
    page_number = request.GET.get('page')
    cmdrs_page = paginator.get_page(page_number)
    
    return render(
        request,
        "stats/single_cmdr_decklist.html",
        context={
            'card': card,
            'decks': cmdrs_page,
            'links': _LINKS,
        },
    )


def hx_common_cards(request, card_id, card_type, page_number):
    if not request.htmx:
        return HttpResponseNotAllowed("expected HTMX request")
    
    card = get_object_or_404(Card, pk=card_id)

    commands_count = (
        Deck.objects
        .filter(
            pdh_legal=True,
            card_list__card=card,
            card_list__is_pdh_commander=True,
        )
        .count()
    )

    match card_type:
        case 'c':
            filter_to = 'Creature'
            card_type_plural = 'creatures'
        case 'a':
            filter_to = 'Artifact'
            card_type_plural = 'artifacts'
        case 'e':
            filter_to = 'Enchantment'
            card_type_plural = 'enchantments'
        case 'i':
            filter_to = 'Instant'
            card_type_plural = 'instants'
        case 's':
            filter_to = 'Sorcery'
            card_type_plural = 'sorceries'
        case 'p':
            filter_to = 'Planeswalker'
            card_type_plural = 'planeswalkers'
        case 'l':
            filter_to = 'Land'
            card_type_plural = 'lands'
        case 'g':
            filter_to = 'Legendary'
            card_type_plural = 'legendaries'
        case _:
            return HttpResponseNotAllowed()

    
    common_cards = (
        CardInDeck.objects
        .filter(
            is_pdh_commander=False,
            deck__in=(
                Deck.objects
                .filter(
                    pdh_legal=True,
                    card_list__card=card,
                )
                .distinct()
            ),
        )
        .exclude(card__type_line__contains='Basic')
        .filter(card__type_line__contains=filter_to)
        .values('card')
        .annotate(count=Count('deck'))
        .values('count', 'card__id', 'card__name')
        .filter(count__gt=1)
        .order_by('-count')
    )
    paginator = Paginator(common_cards, 10, orphans=3)
    cards_page = paginator.get_page(page_number)

    response = render(
        request,
        "stats/hx_common_cards.html",
        context={
            'cmdr_id': card_id,
            'card_type': card_type,
            'card_type_plural': card_type_plural,
            'commands': commands_count,
            'common_cards': cards_page,
        },
    )
    
    return trigger_client_event(
        response,
        "page_move",
        {
            'type': card_type,
            'page': page_number,
        },
        after="settle",
    )


@login_required
@require_POST
def set_editorial_image(request, card_id):
    if not request.htmx:
        return HttpResponseNotAllowed("expected HTMX request")

    if not request.user.is_superuser:
        raise HttpResponseNotAllowed()
    
    printing_id = request.POST['printing_id']
    card = get_object_or_404(Card, pk=card_id)
    printing = get_object_or_404(Printing, pk=printing_id)

    if printing.card != card:
        raise HttpResponseNotAllowed("printing must belong to card")

    card.editorial_printing = printing
    card.save()
    
    return HttpResponseClientRefresh()


def search(request):
    query = request.GET.get('q', '')

    results = (
        Card.objects
        .filter(name__icontains=query)
        .annotate(
            in_decks=Count('deck_list'),
            ninetynine_decks=Count(
                'deck_list',
                filter=Q(deck_list__is_pdh_commander=False),
            ),
            helms_decks=Count(
                'deck_list',
                filter=Q(deck_list__is_pdh_commander=True),
            ),
        )
        .filter(in_decks__gt=0)
        .order_by('-in_decks', 'name')
    )
    paginator = Paginator(results, 25, orphans=3)
    page_number = request.GET.get('page')
    results_page = paginator.get_page(page_number)

    return render(
        request,
        'search/results.html',
        {
            'results': results_page,
            'query': query,
        }
    )
