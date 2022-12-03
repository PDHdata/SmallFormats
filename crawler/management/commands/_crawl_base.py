"""
See https://archidekt.com/forum/thread/3476605/1 for more on crawling Archidekt.
"""
from django.core.management.base import BaseCommand, CommandError
import httpx
from decklist.models import Deck
from crawler.models import CrawlRun
from django.utils import timezone
import time
from crawler.crawlers import CrawlerExit, HEADERS, format_response_error
from ._mixins import LoggingMixin


class CrawlCommand(BaseCommand, LoggingMixin):
    help = f'Ask source for PDH decklists'

    def handle(self, *args, **options):
        sleep_time = 2

        stop_after = self._compute_stop_after()
        run = self._get_or_create_run(stop_after)

        self._log(f"Starting run {run}")

        client: httpx.Client = self._create_client()
        crawler = self.Crawler(
            client,
            run.next_fetch,
            stop_after,
            self._log,
        )
        
        run.state = CrawlRun.State.FETCHING_DECKS
        run.save()
        
        try:
            while crawler.get_next_page():
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
            self._err(f"{e}")
            raise CommandError(str(e))
        
        # if we got here without exiting, we're done
        self._log("Done!")
        run.state = CrawlRun.State.COMPLETE
        run.save()

    def _create_client(self):
        return httpx.Client(
            headers=HEADERS,
            base_url=self.API_BASE,
            event_hooks={
                'request': [self._request_log],
                'response': [self._response_log],
            })
    
    def _compute_stop_after(self):
        try:
            latest_deck_update = (
                Deck.objects
                .filter(
                    source=self.DATASOURCE,
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
                target=self.DATASOURCE,
                state__in=(
                    CrawlRun.State.NOT_STARTED,
                    CrawlRun.State.FETCHING_DECKS,
                )
            ).latest('crawl_start_time')
        except CrawlRun.DoesNotExist:
            run = CrawlRun(
                crawl_start_time=timezone.now(),
                target=self.DATASOURCE,
                state=CrawlRun.State.NOT_STARTED,
                search_back_to=stop_after,
            )
            run.save()

        return run

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
