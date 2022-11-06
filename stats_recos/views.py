from django.shortcuts import render
from django.urls import reverse_lazy
from django.db.models import Count, Q
from decklist.models import Card, Deck, Printing, CardInDeck
from .wubrg_utils import COLORS
import operator
import functools


_CARDS_LINKS = (
    ('Top cards', reverse_lazy('card-top')),
    ('All cards', reverse_lazy('card')),
 )
_CMDRS_LINKS = (
    ('Top commanders', reverse_lazy('cmdr-top')),
    ('All commanders', reverse_lazy('cmdr')),
 )
_LANDS_LINKS = (
    ('Top lands', reverse_lazy('land-top')),
    ('All lands ', reverse_lazy('land')),
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
        .filter(is_pdh_commander=True)
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
        .filter(is_pdh_commander=True)
        .aggregate(count=Count('deck', filter=filter_q, distinct=True))
    )['count']


def stats_index(request):
    return render(
        request,
        "index.html",
        context={
            'links': _LINKS,
        },
    )


def partner_decks(request):
    partner_decks = (
        Deck.objects
        .annotate(num_cmdrs=Count(
            'card_list', filter=Q(card_list__is_pdh_commander=True)
        ))
        .filter(num_cmdrs__gt=1)
    )

    return render(
        request,
        "partner_decks.html",
        context={
            'decks': partner_decks[:20],
            'links': _LINKS,
        },
    )


def commander_index(request):
    return render(
        request,
        "commander_index.html",
        context={
            'colors': [
                (c[0], f'cmdr-{c[0]}') for c in COLORS
            ],
            'links': _LINKS,
        },
    )


def top_commanders(request):
    cmdr_cards = (
        Card.objects
        .filter(deck_list__is_pdh_commander=True)
        .annotate(num_decks=Count('deck_list'))
        .order_by('-num_decks')
    )
    deck_count = Deck.objects.count()

    return render(
        request,
        "commanders.html",
        context={
            'cards': cmdr_cards[:10],
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
            type_line__contains='Creature',
            printings__rarity=Printing.Rarity.UNCOMMON,
        )
        .annotate(num_decks=Count(
            'deck_list',
            distinct=True,
            filter=Q(deck_list__is_pdh_commander=True)
        ))
        .filter(num_decks__gt=0)
        .order_by('-num_decks')
    )

    return render(
        request,
        "commanders.html",
        context={
            'cards': cmdrs,
            # TODO: probably fails to account for partners
            'deck_count': _deck_count_exact_color(w, u, b, r, g),
            'links': _LINKS,
        },
    )


def land_index(request):
    return render(
        request,
        "land_index.html",
        context={
            'colors': [
                (c[0], f'land-{c[0]}') for c in COLORS
            ],
            'links': _LINKS,
        },
    )


def top_lands(request):
    land_cards = (
        Card.objects
        .filter(type_line__contains='Land')
        .annotate(num_decks=Count('deck_list'))
        .order_by('-num_decks')
        .filter(num_decks__gt=0)
    )
    deck_count = Deck.objects.count()

    return render(
        request,
        "lands.html",
        context={
            'cards': land_cards,
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
        .annotate(num_decks=Count('deck_list'))
        .order_by('-num_decks')
        .filter(num_decks__gt=0)
    )

    return render(
        request,
        "lands.html",
        context={
            'cards': land_cards,
            'deck_count': _deck_count_at_least_color(w, u, b, r, g),
            'links': _LINKS,
        },
    )


def card_index(request):
    return render(
        request,
        "card_index.html",
        context={
            'colors': [
                (c[0], f'card-{c[0]}') for c in COLORS
            ],
            'links': _LINKS,
        },
    )


def top_cards(request):
    cards = (
        Card.objects
        .annotate(num_decks=Count('deck_list'))
        .order_by('-num_decks')
    )
    deck_count = Deck.objects.count()

    return render(
        request,
        "cards.html",
        context={
            'cards': cards[:20],
            'deck_count': deck_count,
            'links': _LINKS,
        },
    )


def cards_by_color(request, w=False, u=False, b=False, r=False, g=False):
    card_cards = (
        Card.objects
        .filter(
            identity_w=w,
            identity_u=u,
            identity_b=b,
            identity_r=r,
            identity_g=g,
        )
        .annotate(num_decks=Count('deck_list'))
        .order_by('-num_decks')
        .filter(num_decks__gt=0)
    )

    return render(
        request,
        "cards.html",
        context={
            'cards': card_cards,
            'deck_count': _deck_count_at_least_color(w, u, b, r, g),
            'links': _LINKS,
        },
    )
