"""
See https://archidekt.com/forum/thread/3476605/1 for more on crawling Archidekt.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_datetime
import httpx
from decklist.models import Deck, DataSource
from crawler.models import CrawlRun, DeckCrawlResult
from django.utils import timezone
import time
from ._api_helpers import HEADERS, ARCHIDEKT_API_BASE


# TODO:
# - be able to resume failed/incomplete runs
# - in the commands, target a particular run

def format_response_error(response):
    result = f"{response.status_code} accessing {response.request.url}\n\n"
    for hdr, value in response.headers.items():
        result += f".. {hdr}: {value}\n"
    result += f"\n{response.text}"

    return result

class Command(BaseCommand):
    help = 'Ask Archidekt for PDH decklists'

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '--stop-after',
            type=int, default=0,
            help='Stop crawling after this many pages of results')

    def handle(self, *args, **options):
        sleep_time = 2
        stop_after = options['stop_after']
        retrieved_pages = 0
        crawl_time = timezone.now()
        continue_crawling = False

        try:
            latest_deck_update = (
                Deck.objects
                .filter(
                    source=DataSource.ARCHIDEKT,
                    updated_time__isnull=False,
                )
                .latest('updated_time')
            ).updated_time
            print(f"we will search back to {latest_deck_update}")
        except Deck.DoesNotExist:
            latest_deck_update = None
            print(f"no date to search back to")

        # TODO: search for and resume existing runs
        run = CrawlRun(
            crawl_start_time=crawl_time,
            target=DataSource.ARCHIDEKT,
            state=CrawlRun.State.NOT_STARTED,
            search_back_to=latest_deck_update,
        )
        run.save()

        params = {
            'formats': 17,
            'orderBy': '-createdAt',
            'size': 100,
            'pageSize': 48,
        }
        with httpx.Client(
            headers=HEADERS,
            base_url=ARCHIDEKT_API_BASE,
            follow_redirects=True,
            event_hooks={
                'request': [self._request_log],
                'response': [self._response_log],
            }
        ) as client:
            run.state = CrawlRun.State.FETCHING_DECKS
            run.save()

            decks = client.get("decks/cards/", params=params)
            if 200 <= decks.status_code < 300:
                continue_crawling = True
                envelope = decks.json()
                count, next = envelope['count'], envelope['next']
                if count > 0:
                    self.stdout.write(f"There are {count} decks.")
                results = envelope['results']
            else:
                run.state = CrawlRun.State.ERROR
                run.note = format_response_error(decks)
                run.save()
                self.stderr.write(f"HTTP error {decks.status_code} accessing {decks.request.url}")

            while continue_crawling:
                # default to stopping; we'll flip this later if we should continue
                continue_crawling = False
                # Archidekt seems to send "count = -1" under some conditions
                if count <= 0:
                    run.state = CrawlRun.State.ERROR
                    run.note = format_response_error(decks)
                    run.save()
                    self.stderr.write(f"Received \"{decks.text}\" accessing {decks.request.url}")
                else:
                    oldest_deck_update = self._process_page(run, results)
                    retrieved_pages += 1
                    self.stdout.write(f"Seen {retrieved_pages} pages.")

                if (
                    next and
                    count > 0 and
                    (retrieved_pages < stop_after or stop_after == 0) and
                    (run.search_back_to is None or oldest_deck_update > run.search_back_to)
                ):
                    self.stdout.write(f"Sleeping {sleep_time}s.")
                    time.sleep(sleep_time)
                    # Archidekt "next" comes back as http:// so fix that up
                    if next[0:5] == 'http:':
                        next = 'https:' + next[5:]
                    decks = client.get(next)
                    if 200 <= decks.status_code < 300:
                        continue_crawling = True
                        envelope = decks.json()
                        count, next = envelope['count'], envelope['next']
                        results = envelope['results']
                    else:
                        run.state = CrawlRun.State.ERROR
                        run.note = format_response_error(decks)
                        run.save()
                        self.stderr.write(f"HTTP error {decks.status_code} accessing {decks.request.url}")
            
            # made it to the end
            if run.state == CrawlRun.State.FETCHING_DECKS:
                run.state = CrawlRun.State.DONE_FETCHING_DECKS
                run.save()
                self.stdout.write(self.style.SUCCESS(f"Fetch completed successfully. Now run `populate-archidekt --crawl-id {run.id}`."))

    def _process_page(self, run, results):
        self.stdout.write(f"Processing next {len(results)} results.")
        
        # get existing decks for this page
        ids = [str(r['id']) for r in results]
        qs = Deck.objects.filter(
            source=DataSource.ARCHIDEKT
        ).filter(source_id__in=ids)
        existing_decks = { d.source_id: d for d in qs }

        for deck_data in results:
            this_id = str(deck_data['id'])
            if this_id in existing_decks.keys():
                deck = existing_decks[this_id]
            else:
                deck = Deck()
            deck.name = deck_data['name']
            deck.source = DataSource.ARCHIDEKT
            deck.source_id = this_id
            deck.source_link = f"https://archidekt.com/decks/{this_id}"
            deck.creator_display_name = deck_data['owner']['username']
            deck.updated_time = deck_data['updatedAt']

            crawl_result = DeckCrawlResult(
                url=ARCHIDEKT_API_BASE + f"decks/{this_id}/",
                deck=deck,
                run=run,
                updated_time=deck_data['updatedAt'],
                got_cards=False,
            )
            with transaction.atomic():
                deck.save()
                crawl_result.save()
        
        # the last deck on the page will have the oldest date
        print(f"oldest update_time is {deck.updated_time}")
        return parse_datetime(deck.updated_time)

    def _request_log(self, request):
        self.stdout.write(f">> {request.method} {request.url}")

    def _response_log(self, response):
        request = response.request
        self.stdout.write(f"<< {request.method} {request.url} {response.status_code}")
        if response.status_code >= 400:
            response.read()
            for hdr, value in response.headers.items():
                self.stderr.write(self.style.ERROR(f".. {hdr}: {value}"))
            self.stderr.write("")
            self.stderr.write(self.style.ERROR(response.text))
            self.stderr.write("--------")
