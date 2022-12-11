from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from crawler.models import DeckCrawlResult
from decklist.models import Deck, DataSource


class Command(BaseCommand):
    help = 'Schedule a re-crawl for all Archidekt decks'

    def handle(self, *args, **options):
        now = timezone.now()
        for deck in Deck.objects.filter(source=DataSource.ARCHIDEKT):
            url = f'https://archidekt.com/api/decks/{deck.source_id}/'
            c = DeckCrawlResult(
                deck=deck,
                url=url,
                updated_time=now,
            )
            c.save()
