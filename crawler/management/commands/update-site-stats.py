from django.core.management.base import BaseCommand, CommandError
from django.db.utils import DataError
from django.utils.dateparse import parse_date
import httpx
import json_stream.httpx
from decklist.models import Deck, SiteStat
from ._mixins import LoggingMixin


PROGRESS_EVERY_N_CARDS = 100

class CantParseCardError(Exception): ...

class Command(BaseCommand, LoggingMixin):
    help = 'Ask Scryfall for card data'

    def handle(self, *args, **options):
        legal_decks = (
            Deck.objects
            .filter(pdh_legal=True)
            .count()
        )

        s = SiteStat(legal_decks=legal_decks)
        s.save()
