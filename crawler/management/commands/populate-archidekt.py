from django.core.management.base import BaseCommand, CommandError
import httpx
from decklist.models import DataSource, CardInDeck, Printing
from crawler.models import CrawlRun, DeckCrawlResult
import time
from django.db import transaction
from ._api_helpers import HEADERS, ARCHIDEKT_API_BASE


def format_response_error(response):
    result = f"{response.status_code} accessing {response.request.url}\n\n"
    for hdr, value in response.headers.items():
        result += f".. {hdr}: {value}\n"
    result += f"\n{response.text}"

    return result

class Command(BaseCommand):
    help = 'Populate Archidekt decks retrieved by crawl-archidekt'

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '--crawl-id',
            type=int, default=0,
            help='Retrieve decks for this crawl')

    def handle(self, *args, **options):
        sleep_time = 2

        runs = CrawlRun.objects.filter(
            target=DataSource.ARCHIDEKT,
            state__in=[
                CrawlRun.State.DONE_FETCHING_DECKS,
                CrawlRun.State.FETCHING_DECKLISTS,
            ],
        ).order_by('-crawl_start_time')
        try:
            run = runs.get(pk=options['crawl_id'])
        except CrawlRun.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Crawl {options['crawl_id']} not found or completed."))
            if len(runs) > 0:
                self.stderr.write(f"Perhaps you meant {runs[0].id}?")
            return
        
        self.stdout.write(f"Crawl {run.id} has {run.deck_results.count()} decks to process.")

        with httpx.Client(
            headers=HEADERS,
            base_url=ARCHIDEKT_API_BASE,
            follow_redirects=True,
            event_hooks={
                'request': [self._request_log],
                'response': [self._response_log],
            }
        ) as client:
            run.state = CrawlRun.State.FETCHING_DECKLISTS
            run.save()

            for crawl_result in run.deck_results.all():
                # TODO: no reason for this to be nullable
                if crawl_result.deck is None or crawl_result.got_cards:
                    continue
                
                if run.state == CrawlRun.State.FETCHING_DECKLISTS:
                    response = client.get(crawl_result.url)
                else:
                    break

                if 200 <= response.status_code < 300:
                    envelope = response.json()
                    cards = envelope['cards']
                else:
                    run.state = CrawlRun.State.ERROR
                    run.note = format_response_error(response)
                    run.save()
                    self.stderr.write(f"HTTP error {response.status_code} accessing {response.request.url}")

                if run.state == CrawlRun.State.FETCHING_DECKLISTS:
                    self._process_deck(crawl_result, cards)
                    self.stdout.write(f"Sleeping {sleep_time}s.")
                    time.sleep(sleep_time)
            
            # made it to the end
            if run.state == CrawlRun.State.FETCHING_DECKLISTS:
                run.state = CrawlRun.State.DONE_FETCHING_DECKLISTS
                run.save()
                # TODO: delete all the DeckCrawlResults for this run where
                # `got_cards` is True
                self.stdout.write(self.style.SUCCESS(f"Run {run.id} populated successfully."))
                count, _ = (
                    DeckCrawlResult.objects
                    .filter(run=run, got_cards=True)
                    .delete()
                )
                self.stdout.write(f"Cleaned up {count} records from the run.")
                run.state = CrawlRun.State.COMPLETE
                run.save()

    def _process_deck(self, crawl_result, cards):
        # resolve printings to cards
        lookup_printings = set()
        for card_json in cards:
            printing_id = card_json['card']['uid']
            lookup_printings.add(printing_id)
        print_id_to_card = {
            str(p.id): p.card
            for p in Printing.objects.filter(id__in=lookup_printings)
        }

        # reuse cards where we can
        # TODO: handle multiple printings of the same card
        current_cards = {
            c.card.id: c for c in CardInDeck.objects.filter(deck=crawl_result.deck)
        }
        update_cards = []
        new_cards = []

        for card_json in cards:
            printing_id = card_json['card']['uid']
            if printing_id not in print_id_to_card.keys():
                self.stderr.write(f"skipping printing {printing_id}; did not resolve to a card")
                continue
            card_id = print_id_to_card[printing_id].id
            if card_id in current_cards.keys():
                # self.stdout.write(f"reuse card {card_id}")
                reuse_card = current_cards.pop(card_id)
                reuse_card.is_pdh_commander = "Commander" in card_json['categories']
                update_cards.append(reuse_card)
            else:
                # self.stdout.write(f"appending new card for card {card_id}")
                new_cards.append(CardInDeck(
                    deck=crawl_result.deck,
                    card=print_id_to_card[printing_id],
                    is_pdh_commander="Commander" in card_json['categories'],
                ))
        
        with transaction.atomic():
            (
                CardInDeck.objects
                .filter(deck=crawl_result.deck)
                .filter(card__id__in=current_cards.keys())
                .delete()
            )
            CardInDeck.objects.bulk_create(new_cards)
            CardInDeck.objects.bulk_update(update_cards, ['is_pdh_commander'])
            crawl_result.got_cards = True
            crawl_result.save()

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
