from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Q
from decklist.models import Card, Printing, Deck, CardInDeck


class Command(BaseCommand):
    help = 'stats playground'

    def handle(self, *args, **options):
        # raw top 10
        print("raw top 10")
        raw_cards = (
            Card.objects
            .annotate(num_decks=Count('deck_list'))
            .order_by('-num_decks')
        )
        for c in raw_cards[:10]:
            print(f"{c} in {c.num_decks} decks")
        print("---")

        # top 10 commanders
        print("top 10 commanders")
        cmdr_cards = (
            Card.objects
            .filter(deck_list__is_pdh_commander=True)
            .annotate(num_decks=Count('deck_list'))
            .order_by('-num_decks')
        )
        for c in cmdr_cards[:10]:
            print(f"{c} in {c.num_decks} decks")
        print("---")

        # partner decks
        print("10 partner decks")
        partner_decks = (
            Deck.objects
            .annotate(num_cmdrs=Count(
                'card_list', filter=Q(card_list__is_pdh_commander=True)
            ))
            .filter(num_cmdrs__gt=1)
        )
        for d in partner_decks[:10]:
            print(f"{d} ({d.num_cmdrs})")
        print("---")

        # identities on decks
        print("10 decks with their identities")
        ident_decks = (
            Deck.objects
            .annotate(
                white=Count(
                    'card_list',
                    filter=Q(card_list__card__identity_w=True)
                         & Q(card_list__is_pdh_commander=True),
                    distinct=True,
                ),
                blue=Count(
                    'card_list',
                    filter=Q(card_list__card__identity_u=True)
                         & Q(card_list__is_pdh_commander=True),
                    distinct=True,
                ),
                black=Count(
                    'card_list',
                    filter=Q(card_list__card__identity_b=True)
                         & Q(card_list__is_pdh_commander=True),
                    distinct=True,
                ),
                red=Count(
                    'card_list',
                    filter=Q(card_list__card__identity_r=True)
                         & Q(card_list__is_pdh_commander=True),
                    distinct=True,
                ),
                green=Count(
                    'card_list',
                    filter=Q(card_list__card__identity_g=True)
                         & Q(card_list__is_pdh_commander=True),
                    distinct=True,
                ),
            )
        )
        for d in ident_decks[:10]:
            print(f"{d} ({d.white} {d.blue} {d.black} {d.red} {d.green})")
        print("---")

        # boros decks
        print("10 boros decks")
        boros_decks = (
            ident_decks
            .filter(white__gt=0, blue=0, black=0, red__gt=0, green=0)
        )
        for d in boros_decks[:10]:
            print(f"{d}")
        print("---")