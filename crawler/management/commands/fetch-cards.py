"""
See https://scryfall.com/docs/api/bulk-data for more on Scryfall data.
"""
from django.core.management.base import BaseCommand, CommandError
import httpx
import json_stream
from decklist.models import Card, Printing

class Command(BaseCommand):
    help = 'Ask Scryfall for card data'

    def handle(self, *args, **options):
        # TODO: stream from Scryfall API
        with open("default-cards.json") as f:
            for json_card in json_stream.load(f).persistent():
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
                c.save()
                p.save()
                self.stdout.write(f"{json_card['name']} ({json_card['set']})")
