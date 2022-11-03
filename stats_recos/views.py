from django.shortcuts import render
from django.db.models import Count, Q
from decklist.models import Card, Deck


def top_commanders(request):
    cmdr_cards = (
        Card.objects
        .filter(deck_list__is_pdh_commander=True)
        .annotate(num_decks=Count('deck_list'))
        .order_by('-num_decks')
    )

    return render(
        request,
        "card_num_decks.txt",
        context={
            'cards': cmdr_cards[:10],
        },
        content_type="text/plain",
    )


def top_cards(request):
    cards = (
        Card.objects
        .annotate(num_decks=Count('deck_list'))
        .order_by('-num_decks')
    )

    return render(
        request,
        "card_num_decks.txt",
        context={
            'cards': cards[:20],
        },
        content_type="text/plain",
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
        "partner_decks.txt",
        context={
            'decks': partner_decks[:20],
        },
        content_type="text/plain",
    )
