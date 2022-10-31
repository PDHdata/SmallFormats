from django.core.management.base import BaseCommand, CommandError
import httpx
from decklist.models import Deck, DataSource
from crawler.models import DeckCrawlResult
from django.utils import timezone
import time


ARCHIDEKT_API_BASE = "https://archidekt.com/api/"
HEADERS = {
    'User-agent': 'SmallFormats/0.1.0',
}

class Command(BaseCommand):
    help = 'Ask Archidekt for PDH decklists'

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '--stop-after',
            type=int, default=3,
            help='Stop crawling after this many pages of results; use 0 to remove the limit')

    def handle(self, *args, **options):
        stop_after = options['stop_after']
        retrieved_pages = 0
        crawl_time = timezone.now()
        continue_crawling = False

        params = {
            'formats': 17,
            'orderBy': '-createdAt',
            'size': 100,
            'pageSize': 48,
        }
        with httpx.Client(headers=HEADERS, base_url=ARCHIDEKT_API_BASE, follow_redirects=True) as client:
            decks = client.get("decks/cards/", params=params)
            if 200 <= decks.status_code < 300:
                continue_crawling = True
                envelope = decks.json()
                count, next = envelope['count'], envelope['next']
                self.stdout.write(f"There are {count} decks.")
                results = envelope['results']
            else:
                self.stderr.write(f"HTTP error {decks.status_code} accessing {decks.request.url}")

            while continue_crawling:
                # default to stopping; we'll flip this later if we should continue
                continue_crawling = False
                self._process_page(crawl_time, results)
                retrieved_pages += 1
                self.stdout.write(f"processed {retrieved_pages} pages")

                if retrieved_pages < stop_after or stop_after == 0:
                    self.stdout.write("...sleeping...")
                    time.sleep(2)
                    decks = client.get(next)
                    if 200 <= decks.status_code < 300:
                        continue_crawling = True
                        envelope = decks.json()
                        next = envelope['next']
                        results = envelope['results']
                    else:
                        self.stderr.write(f"HTTP error {decks.status_code} accessing {decks.request.url}")

    def _process_page(self, crawl_time, results):
        self.stdout.write(f"Processing next {len(results)} results.")
        for deck_data in results:
            # TODO: bulk lookup decks to make sure they don't exist yet
            deck = Deck(
                name=deck_data['name'],
                source=DataSource.ARCHIDEKT,
                source_id=str(deck_data['id']),
                source_link='', # TODO
                creator_display_name=deck_data['owner']['username'],
                updated_time=deck_data['updatedAt'],
            )
            crawl_result = DeckCrawlResult(
                crawl_time=crawl_time,
                url="https://todo.example.com",
                deck=deck,
                updated_time=deck_data['updatedAt'],
                got_cards=False, # TODO: write crawler for cards
            )
            deck.save()
            crawl_result.save()

