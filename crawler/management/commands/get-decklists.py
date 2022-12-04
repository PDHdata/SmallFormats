from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import httpx
from decklist.models import DataSource, Printing, CardInDeck
from crawler.models import DeckCrawlResult
from ._mixins import LoggingMixin
import time
from itertools import chain
from crawler.crawlers import HEADERS


class Command(BaseCommand, LoggingMixin):
    help = 'Populate any decks retrieved by the crawlers'

    def handle(self, *args, **options):
        sleep_time = 2

        updatable_decks = (
            DeckCrawlResult.objects
            .filter(fetchable=True, got_cards=False)
        )

        with httpx.Client(headers=HEADERS) as client:
            for updatable_deck in updatable_decks:
                response = client.get(updatable_deck.url)
                if 200 <= response.status_code < 300:
                    deck_name = updatable_deck.deck.name
                    new_deck = True if updatable_deck.deck.card_list.count() == 0 else False
                    verb = "Creating" if new_deck else "Updating"
                    envelope = response.json()
                    if updatable_deck.deck.source == DataSource.ARCHIDEKT:
                        self._log(f"{verb} \"{deck_name}\" (Archidekt)")
                        self._process_architekt_deck(updatable_deck, envelope['cards'])
                    elif updatable_deck.deck.source == DataSource.MOXFIELD:
                        self._log(f"{verb} \"{deck_name}\" (Moxfield)")
                        self._process_moxfield_deck(updatable_deck, envelope)
                    else:
                        self._err(f"Can't update \"{deck_name}\", unimplemented source")
                        updatable_deck.fetchable = False
                        updatable_deck.save()
                elif response.status_code in (400, 404):
                    # mark deck as unfetchable and carry on
                    self._log(f"Got error {response.status_code} for \"{updatable_deck.deck.name}\" ({updatable_deck.url}).")
                    updatable_deck.fetchable = False
                    updatable_deck.save()
                else:
                    self._err(f"Got {response.status_code} from server. ({response.url})")
                    updatable_deck.fetchable = False
                    updatable_deck.save()

                if updatable_deck.got_cards:
                    updatable_deck.deck.deckcrawlresult_set.all().delete()
                
                time.sleep(sleep_time)
        
        self._log("Done!")

    def _process_architekt_deck(self, crawl_result, cards):
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
        # TODO: handle multiple printings of the same card?
        current_cards = {
            c.card.id: c for c in CardInDeck.objects.filter(deck=crawl_result.deck)
        }
        update_cards = []
        new_cards = []

        for card_json in cards:
            printing_id = card_json['card']['uid']
            if printing_id not in print_id_to_card.keys():
                name = card_json['card']['oracleCard']['name']
                edition = card_json['card']['edition']['editioncode']
                self._err(f"could not resolve printing {printing_id}; should be \"{name}\" ({edition})")
                continue
            card_id = print_id_to_card[printing_id].id
            if card_id in current_cards.keys():
                reuse_card = current_cards.pop(card_id)
                reuse_card.is_pdh_commander = "Commander" in card_json['categories']
                update_cards.append(reuse_card)
            else:
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


    def _process_moxfield_deck(self, crawl_result, envelope):
        # resolve printings to cards
        cards = envelope['mainboard']
        cmdrs = envelope['commanders']

        lookup_printings = set()
        for _, card_json in chain(cards.items(), cmdrs.items()):
            printing_id = card_json['card']['scryfall_id']
            lookup_printings.add(printing_id)
        print_id_to_card = {
            str(p.id): p.card
            for p in Printing.objects.filter(id__in=lookup_printings)
        }

        # reuse cards where we can
        current_cards = {
            c.card.id: c for c in CardInDeck.objects.filter(deck=crawl_result.deck)
        }
        update_cards = []
        new_cards = []

        for card_set, is_commander in ((cards, False), (cmdrs, True)):
            for _, card_json in card_set.items():
                printing_id = card_json['card']['scryfall_id']
                if printing_id not in print_id_to_card.keys():
                    name = card_json['card']['name']
                    edition = card_json['card']['set']
                    self._err(f"could not resolve printing {printing_id}; should be \"{name}\" ({edition})")
                    continue
                card_id = print_id_to_card[printing_id].id
                if card_id in current_cards.keys():
                    reuse_card = current_cards.pop(card_id)
                    reuse_card.is_pdh_commander = is_commander
                    update_cards.append(reuse_card)
                else:
                    new_cards.append(CardInDeck(
                        deck=crawl_result.deck,
                        card=print_id_to_card[printing_id],
                        is_pdh_commander=is_commander,
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
