"""
See https://scryfall.com/docs/api/bulk-data for more on Scryfall data.
"""
from django.core.management.base import BaseCommand, CommandError
import httpx
from ._httpx_json_stream import httpx_load
from decklist.models import Card, Printing
from ._api_helpers import HEADERS, SCRYFALL_API_BASE


class CantParseCardError(Exception): ...

class Command(BaseCommand):
    help = 'Ask Scryfall for card data'

    def handle(self, *args, **options):
        self.stdout.write(f"begin: {Card.objects.all().count()} cards, {Printing.objects.all().count()} printings")
        with httpx.Client(base_url=SCRYFALL_API_BASE, headers=HEADERS) as client:
            result = client.get("bulk-data/default-cards")
            result.raise_for_status()
            download_target = result.json()["download_uri"]
            self.stdout.write(f"Fetching {download_target}")

            with client.stream('GET', download_target) as f:
                for json_card in httpx_load(f).persistent():
                    for parse in [self._extract_card_and_printing, self._extract_verhey_card_and_printing]:
                        try:
                            c, p = parse(json_card)
                        except CantParseCardError:
                            ... # try the next method
                        
                        if c and p: break
                    
                    if c and p:
                        c.save()
                        p.save()
                    else:
                        self.stderr.write(f"failed to parse {json_card['name']}")

        self.stdout.write(f"end: {Card.objects.all().count()} cards, {Printing.objects.all().count()} printings")

    def _extract_card_and_printing(self, json_card):
        try:
            c = Card(
                id=json_card['oracle_id'],
                name=json_card['name'],
                identity_w="W" in json_card['color_identity'],
                identity_u="U" in json_card['color_identity'],
                identity_b="B" in json_card['color_identity'],
                identity_r="R" in json_card['color_identity'],
                identity_g="G" in json_card['color_identity'],
                type_line=json_card['type_line'],
            )
            p = Printing(
                id=json_card['id'],
                card=c,
                set_code=json_card['set'],
                rarity=Printing.Rarity[json_card['rarity'].upper()],
            )
            return c, p
        except KeyError:
            raise CantParseCardError()

    def _extract_verhey_card_and_printing(self, json_card):
        # Gavin Verhey's Commander deck has double-sided reprints of
        # single-sided cards, e.g. https://scryfall.com/card/sld/381/propaganda-propaganda
        if json_card['card_faces'][0]['oracle_id'] == json_card['card_faces'][1]['oracle_id']:
            try:
                face = json_card['card_faces'][0]
                c = Card(
                    id=face['oracle_id'],
                    name=face['name'],
                    identity_w="W" in json_card['color_identity'],
                    identity_u="U" in json_card['color_identity'],
                    identity_b="B" in json_card['color_identity'],
                    identity_r="R" in json_card['color_identity'],
                    identity_g="G" in json_card['color_identity'],
                    type_line=face['type_line'],
                )
                p = Printing(
                    id=json_card['id'],
                    card=c,
                    set_code=json_card['set'],
                    rarity=Printing.Rarity[json_card['rarity'].upper()],
                )
                return c, p
            except Exception as ex:
                raise CantParseCardError() from ex

        raise CantParseCardError("card face oracle_ids don't match")