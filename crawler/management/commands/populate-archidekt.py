from django.core.management.base import BaseCommand, CommandError
import httpx
from decklist.models import DataSource, CardInDeck, Printing
from crawler.models import DeckCrawlResult
import time
from django.db import transaction
from ._api_helpers import HEADERS, ARCHIDEKT_API_BASE, format_response_error


class Command(BaseCommand):
    help = 'Populate Archidekt decks retrieved by crawl-archidekt'

    def handle(self, *args, **options):
        sleep_time = 2

        with httpx.Client(
            headers=HEADERS,
            base_url=ARCHIDEKT_API_BASE,
            follow_redirects=True,
            event_hooks={
                'request': [self._request_log],
                'response': [self._response_log],
            }
        ) as client:
            to_fetch = (
                DeckCrawlResult.objects
                .filter(
                    target=DataSource.ARCHIDEKT,
                    got_cards=False,
                )
            )
            for crawl_result in to_fetch:
                response = client.get(crawl_result.url)

                if 200 <= response.status_code < 300:
                    envelope = response.json()
                    cards = envelope['cards']
                    self._process_deck(crawl_result, cards)
                elif response.status_code == 400:
                    self.stderr.write(f"Got 400, skipping {crawl_result.url}")
                    crawl_result.delete()
                else:
                    self.stderr.write(f"HTTP error {response.status_code} accessing {response.request.url}")
                    return

                time.sleep(sleep_time)
            
            # made it to the end
            # delete all the DeckCrawlResults where `got_cards` is True
            count, _ = (
                DeckCrawlResult.objects
                .filter(got_cards=True)
                .delete()
            )
            self.stdout.write(f"Cleaned up {count} records.")

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
        
        # now see if the deck is legal before completing processing
        crawl_result.deck.pdh_legal, _ = crawl_result.deck.check_deck_legality()

        with transaction.atomic():
            crawl_result.deck.save()
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
