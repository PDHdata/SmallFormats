from django.shortcuts import render
from django.urls import reverse
from django.db.models import Count, Sum, Q
from decklist.models import Card, Deck, Printing
from .wubrg_utils import COLORS


def stats_index(request):
    links = (
        ('Cards', reverse('card')),
        ('Commanders', reverse('cmdr')),
        ('Lands', reverse('land')),
        ('Partner decks', reverse('partner-decks')),
    )
    return render(
        request,
        "index.html",
        context={
            'links': links,
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
    # FIXME: this math is wrong, it doesn't count distinct decks
    decks_of_color = cmdrs.aggregate(Sum('num_decks'))['num_decks__sum']

    return render(
        request,
        "commanders.html",
        context={
            'cards': cmdrs,
            'deck_count': decks_of_color,
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
    deck_count = Deck.objects.count()

    return render(
        request,
        "lands.html",
        context={
            'cards': land_cards,
            'deck_count': deck_count,
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
    # TODO: count how many decks contain this color identity
    deck_count = 0

    return render(
        request,
        "cards.html",
        context={
            'cards': card_cards,
            'deck_count': deck_count,
        },
    )
