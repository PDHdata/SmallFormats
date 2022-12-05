from django.core.management.base import BaseCommand, CommandError
from decklist.models import Deck, SiteStat
from ._mixins import LoggingMixin


class Command(BaseCommand, LoggingMixin):
    help = 'Update site stats'

    def handle(self, *args, **options):
        legal_decks = (
            Deck.objects
            .filter(pdh_legal=True)
            .count()
        )

        s = SiteStat(legal_decks=legal_decks)
        s.save()
