from django.shortcuts import render
from django.db.models import Count, Sum, Q
from decklist.models import Card, Deck, Printing
from .wubrg_utils import COLORS


def top_cards(request):
    cards = (
        Card.objects
        .annotate(num_decks=Count('deck_list'))
        .order_by('-num_decks')
    )

    return render(
        request,
        "card_num_decks.html",
        context={
            'cards': cards[:20],
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


def commander_colors(request):
    return render(
        request,
        "commander_colors.html",
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
        "card_num_commands.html",
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
    decks_of_color = cmdrs.aggregate(Sum('num_decks'))['num_decks__sum']

    return render(
        request,
        "card_num_commands.html",
        context={
            'cards': cmdrs,
            'deck_count': decks_of_color,
        },
    )


def land_colors(request):
    return render(
        request,
        "land_colors.html",
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
