from django.db import transaction
import httpx
from decklist.models import DataSource, Printing, Card, CardInDeck
from crawler.models import DeckCrawlResult
from ._command_base import LoggingBaseCommand
import time
from itertools import chain
from crawler.crawlers import HEADERS


def get_known_printings(cards, get_printing_id):
    lookup_printings = set()
    for card_json in cards:
        printing_id = get_printing_id(card_json)
        lookup_printings.add(printing_id)
    return {
        str(p.id): p.card
        for p in Printing.objects.filter(id__in=lookup_printings)
    }


def lookup_card(name, set_code):
    p = (
        Printing.objects
        .filter(
            card__name__iexact=name,
            set_code__iexact=set_code,
        )
        .first()
    )
    if p:
        return p.card

    # HACK:
    # cards with set_code `j21` often don't resolve
    # so we relax the restriction and try again
    if set_code == 'j21':
        c = (
            Card.objects
            .filter(name__iexact=name)
            .first()
        )
        if c:
            return c
    # /HACK

    raise CardNotFound(f'"{name}" ({set_code})')


class CardNotFound(Exception): ...


class Command(LoggingBaseCommand):
    help = 'Populate any decks retrieved by the crawlers'

    def handle(self, *args, **options):
        super().handle(*args, **options)

        sleep_time = 2

        updatable_decks = (
            DeckCrawlResult.objects
            .filter(fetchable=True, got_cards=False)
        )

        self._log(f"Fetching up to {len(updatable_decks)} decks")

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
                        self._process_archidekt_deck(updatable_deck, envelope)
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

    def _process_archidekt_deck(self, crawl_result, envelope):
        # resolve printings to cards
        cards = envelope['cards']
        print_id_to_card = get_known_printings(cards, lambda j: j['card']['uid'])

        # determine categories to skip, categories which are commander
        skip_categories = frozenset([
            cat['name'] for cat in envelope['categories']
            if not cat['includedInDeck']
        ])
        premier_categories = frozenset([
            cat['name'] for cat in envelope['categories']
            if cat['isPremier']
        ])

        # reuse cards where we can
        # TODO: handle multiple printings of the same card?
        current_cards = {
            c.card.id: c for c in CardInDeck.objects.filter(deck=crawl_result.deck)
        }
        update_cards = []
        new_cards = []

        for card_json in cards:
            card_categories = set(card_json['categories'])
            # if card is in a non-included category, skip it
            if not card_categories.isdisjoint(skip_categories):
                continue
            
            # if card is in a premier category, it is a commander
            is_commander = not card_categories.isdisjoint(premier_categories)

            printing_id = card_json['card']['uid']
            if printing_id in print_id_to_card.keys():
                card = print_id_to_card[printing_id]
            else:
                name = card_json['card']['oracleCard']['name']
                edition = card_json['card']['edition']['editioncode']
                try:
                    card = lookup_card(name, edition)
                    self._log(f'Had to look up "{name}" ({edition})')
                except CardNotFound:
                    self._err(f'Could not resolve printing {printing_id}; should be "{name}" ({edition})')
                    continue
            
            if card.id in current_cards.keys():
                reuse_card = current_cards.pop(card.id)
                reuse_card.is_pdh_commander = is_commander
                update_cards.append(reuse_card)
            else:
                new_cards.append(CardInDeck(
                    deck=crawl_result.deck,
                    card=card,
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


    def _process_moxfield_deck(self, crawl_result, envelope):
        # resolve printings to cards
        cards = envelope['mainboard']
        cmdrs = envelope['commanders']

        print_id_to_card = get_known_printings(
            [c for _, c in chain(cards.items(), cmdrs.items())],
            lambda j: j['card']['scryfall_id'],
        )

        # reuse cards where we can
        current_cards = {
            c.card.id: c for c in CardInDeck.objects.filter(deck=crawl_result.deck)
        }
        update_cards = []
        new_cards = []

        for card_set, is_commander in ((cards, False), (cmdrs, True)):
            for _, card_json in card_set.items():
                printing_id = card_json['card']['scryfall_id']
                if printing_id in print_id_to_card.keys():
                    card = print_id_to_card[printing_id]
                else:
                    name = card_json['card']['name']
                    edition = card_json['card']['set']
                    try:
                        card = lookup_card(name, edition)
                        self._log(f'Had to look up "{name}" ({edition})')
                    except CardNotFound:
                        self._err(f'Could not resolve printing {printing_id}; should be "{name}" ({edition})')
                        continue
                
                if card.id in current_cards.keys():
                    reuse_card = current_cards.pop(card.id)
                    reuse_card.is_pdh_commander = is_commander
                    update_cards.append(reuse_card)
                else:
                    new_cards.append(CardInDeck(
                        deck=crawl_result.deck,
                        card=card,
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
