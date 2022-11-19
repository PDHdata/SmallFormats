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
from ._api_helpers import HEADERS, ARCHIDEKT_API_BASE, format_response_error
from crawler.crawlers import ArchidektCrawler, CrawlerExit


class Command(BaseCommand):
    help = 'Ask Archidekt for PDH decklists'

    def handle(self, *args, **options):
        # TODO: introduce an option for resuming an error'd run
        sleep_time = 2

        stop_after = self._compute_stop_after()
        run = self._get_or_create_run(stop_after)

        client: httpx.Client = self._create_client()
        url = (
            self._initial_url(client) if run.state == CrawlRun.State.NOT_STARTED
            else run.next_fetch
        )

        processor = self._process_page
        crawler = ArchidektCrawler(url, stop_after, processor)
        
        run.state = CrawlRun.State.FETCHING_DECKS
        run.save()
        
        try:
            while crawler.get_next_page(client):
                run.next_fetch = crawler.url
                run.save()
                time.sleep(sleep_time)

        except CrawlerExit as e:
            # TODO: check for 429. that's not fatal, it means we need
            # to slow down.
            run.state = CrawlRun.State.ERROR
            run.note = (
                format_response_error(e.respose) if e.response
                else str(e)
            )
            run.save()
            self.stderr.write(f"{e}")
            return
        
        # if we got here without exiting, we're done
        run.state = CrawlRun.State.COMPLETE
        run.save()

    def _create_client(self):
        return httpx.Client(
            headers=HEADERS,
            base_url=ARCHIDEKT_API_BASE,
            follow_redirects=True,
            event_hooks={
                'request': [self._request_log],
                'response': [self._response_log],
            })
    
    def _initial_url(self, client: httpx.Client):
        params = {
            'formats': 17,
            'orderBy': '-createdAt',
            'size': 100,
            'pageSize': 48,
        }
        req = client.build_request(
            "GET",
            "decks/cards/",
            params=params
        )
        return req.url
    
    def _compute_stop_after(self):
        try:
            latest_deck_update = (
                Deck.objects
                .filter(
                    source=DataSource.ARCHIDEKT,
                    updated_time__isnull=False,
                )
                .latest('updated_time')
            ).updated_time
        except Deck.DoesNotExist:
            latest_deck_update = None
        
        return latest_deck_update

    def _get_or_create_run(self, stop_after):
        # try to resume an existing run
        try:
            run = CrawlRun.objects.filter(
                target=DataSource.ARCHIDEKT,
                state__in=(
                    CrawlRun.State.NOT_STARTED,
                    CrawlRun.State.FETCHING_DECKS,
                )
            ).latest('crawl_start_time')
        except CrawlRun.DoesNotExist:
            run = CrawlRun(
                crawl_start_time=timezone.now(),
                target=DataSource.ARCHIDEKT,
                state=CrawlRun.State.NOT_STARTED,
                search_back_to=stop_after,
            )
            run.save()

        return run

    def _process_page(self, results, stop_after):
        self.stdout.write(f"Processing next {len(results)} results.")
        
        # get existing decks for this page
        ids = [str(r['id']) for r in results]
        qs = Deck.objects.filter(
            source=DataSource.ARCHIDEKT
        ).filter(source_id__in=ids)
        existing_decks = { d.source_id: d for d in qs }

        for deck_data in results:
            deck_updated_at = parse_datetime(deck_data['updatedAt'])
            if stop_after and deck_updated_at < stop_after:
                # break if we've seen everything back to the right time
                return deck_updated_at

            this_id = str(deck_data['id'])
            if this_id in existing_decks.keys():
                deck = existing_decks[this_id]
            else:
                deck = Deck()
                deck.pdh_legal = False # until proven otherwise!
            deck.name = deck_data['name']
            deck.source = DataSource.ARCHIDEKT
            deck.source_id = this_id
            deck.source_link = f"https://archidekt.com/decks/{this_id}"
            deck.creator_display_name = deck_data['owner']['username']
            deck.updated_time = deck_updated_at

            crawl_result = DeckCrawlResult(
                url=ARCHIDEKT_API_BASE + f"decks/{this_id}/",
                deck=deck,
                target=DataSource.ARCHIDEKT,
                updated_time=deck_data['updatedAt'],
                got_cards=False,
            )
            with transaction.atomic():
                deck.save()
                crawl_result.save()
        
        # the last deck we processed will have the oldest date
        return deck_updated_at

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
