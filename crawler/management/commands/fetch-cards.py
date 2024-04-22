"""
See https://scryfall.com/docs/api/bulk-data for more on Scryfall data.
"""
from django.db.utils import DataError
from django.utils.dateparse import parse_date
import httpx
import json_stream.httpx
# don't use Rust-based tokenizer
# it throws an OSError about incomplete utf-8 sequences
from json_stream.tokenizer import tokenize
from decklist.models import Card, Printing, PartnerType, Rarity
from crawler.crawlers import HEADERS, SCRYFALL_API_BASE
from crawler.card_parsing import parse_card_and_printing, FailedToParseCard
from ._command_base import LoggingBaseCommand


PROGRESS_EVERY_N_CARDS = 100

class Command(LoggingBaseCommand):
    help = 'Ask Scryfall for card data'

    def handle(self, *args, **options):
        super().handle(*args, **options)

        self._log(f"Fetch cards begin: {Card.objects.all().count()} cards, {Printing.objects.all().count()} printings")
        with httpx.Client(base_url=SCRYFALL_API_BASE, headers=HEADERS) as client:
            result = client.get("bulk-data/default-cards", timeout=httpx.Timeout(10.0))
            if result.is_error:
                self._err(f"{result.status_code}: {result.reason_phrase}")
            result.raise_for_status()
            download_target = result.json()["download_uri"]
            self._log(f"Fetching {download_target}")

            card_count = PROGRESS_EVERY_N_CARDS
            with client.stream('GET', download_target) as f:
                for json_card in json_stream.httpx.load(f, tokenizer=tokenize).persistent():
                    card_count -= 1
                    if card_count <= 0:
                        self.stdout.write('.', ending='')
                        self.stdout.flush()
                        card_count = PROGRESS_EVERY_N_CARDS
                    
                    if not self._want_card(json_card):
                        continue

                    try:
                        c, p = parse_card_and_printing(json_card)

                    except FailedToParseCard as e:                    
                        self._err(f"failed to parse {json_card['name']}")
                        for k, v in e.args[0].items():
                            self._err(f".. {k}: {v}")
                        continue

                    try:
                        if len(c.name) > 100:
                            # Market Research Elemental 🙄
                            c.name = c.name[:47] + '...'
                        c.save()
                        p.save()
                    except DataError as e:
                        self._log(f"Card {c.name} or printing {p} threw {e}")

        self.stdout.write('')
        self._log(f"end: {Card.objects.all().count()} cards, {Printing.objects.all().count()} printings")

    def _want_card(self, json_card):
        # we want to exclude some non-playable cards but aren't entirely
        # beholden to upstream's record of format legalities
        if 'layout' in json_card and json_card['layout'] in (
            'planar', 'scheme', 'vanguard', 'token', 'double_faced_token',
            'emblem', 'art_series', 'reversible_card',
        ):
            return False

        return True
