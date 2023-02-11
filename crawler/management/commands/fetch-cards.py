"""
See https://scryfall.com/docs/api/bulk-data for more on Scryfall data.
"""
from django.db.utils import DataError
from django.utils.dateparse import parse_date
import httpx
import json_stream.httpx
from decklist.models import Card, Printing, PartnerType, Rarity
from crawler.crawlers import HEADERS, SCRYFALL_API_BASE
from ._command_base import LoggingBaseCommand


PROGRESS_EVERY_N_CARDS = 100

class CantParseCardError(Exception): ...

class Command(LoggingBaseCommand):
    help = 'Ask Scryfall for card data'

    def handle(self, *args, **options):
        super().handle(*args, **options)

        self._log(f"Fetch cards begin: {Card.objects.all().count()} cards, {Printing.objects.all().count()} printings")
        with httpx.Client(base_url=SCRYFALL_API_BASE, headers=HEADERS) as client:
            result = client.get("bulk-data/default-cards")
            result.raise_for_status()
            download_target = result.json()["download_uri"]
            self._log(f"Fetching {download_target}")

            card_count = PROGRESS_EVERY_N_CARDS
            with client.stream('GET', download_target) as f:
                for json_card in json_stream.httpx.load(f).persistent():
                    card_count -= 1
                    if card_count <= 0:
                        self.stdout.write('.', ending='')
                        self.stdout.flush()
                        card_count = PROGRESS_EVERY_N_CARDS
                    for parse in [self._extract_card_and_printing, self._extract_verhey_card_and_printing]:
                        try:
                            c, p = parse(json_card)
                        except CantParseCardError:
                            ... # try the next method
                        
                        if c and p: break
                    
                    if not c or not p:
                        self._err(f"failed to parse {json_card['name']}")

                    elif self._want_card(json_card):
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
                keywords=list(json_card['keywords']),
                scryfall_uri=json_card['scryfall_uri'],
            )
            p = Printing(
                id=json_card['id'],
                card=c,
                set_code=json_card['set'],
                rarity=Rarity[json_card['rarity'].upper()],
                is_highres=json_card['highres_image'],
                is_paper="paper" in json_card['games'],
                release_date=parse_date(json_card['released_at']),
            )

            # single-faced card
            if 'image_uris' in json_card:
                p.image_uri = json_card['image_uris'].get('normal')
            
            # front of double-faced card
            elif 'card_faces' in json_card and 'image_uris' in json_card['card_faces'][0]:
                p.image_uri = json_card['card_faces'][0]['image_uris'].get('normal')
            
            # determine partnership
            keywords = json_card['keywords']
            oracle_text = json_card['oracle_text']
            type_line = json_card['type_line']
            c.partner_type = self._determine_partnership(
                keywords, oracle_text, type_line
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
                    keywords=list(json_card['keywords']),
                    scryfall_uri=json_card['scryfall_uri'],
                )
                p = Printing(
                    id=json_card['id'],
                    card=c,
                    set_code=json_card['set'],
                    rarity=Rarity[json_card['rarity'].upper()],
                    is_highres=json_card['highres_image'],
                    is_paper="paper" in json_card['games'],
                    release_date=parse_date(json_card['released_at']),
                )
                if 'image_uris' in face:
                    p.image_uri = face['image_uris'].get('normal')

                # determine partnership
                keywords = json_card['keywords']
                oracle_text = face['oracle_text']
                type_line = face['type_line']
                c.partner_type = self._determine_partnership(
                    keywords, oracle_text, type_line
                )

                return c, p
            except Exception as ex:
                raise CantParseCardError() from ex

        raise CantParseCardError("card face oracle_ids don't match")

    def _determine_partnership(self, keywords, oracle_text, type_line):
        if 'Partner with' in keywords:
            return self._determine_partner_with(oracle_text)
        elif 'Partner' in keywords:
            return PartnerType.PARTNER
        elif 'Choose a Background' in oracle_text:
            return PartnerType.CHOOSE_A_BACKGROUND
        elif 'Background' in type_line:
            return PartnerType.BACKGROUND
        
        return PartnerType.NONE

    def _determine_partner_with(self, oracle_text):
        if 'Partner with Blaring' in oracle_text:
            return PartnerType.PARTNER_WITH_BLARING

        elif 'Partner with Chakram' in oracle_text:
            return PartnerType.PARTNER_WITH_CHAKRAM

        elif 'Partner with Proud Mentor' in oracle_text:
            return PartnerType.PARTNER_WITH_PROTEGE
        elif 'Partner with Impetuous Protege' in oracle_text:
            return PartnerType.PARTNER_WITH_PROTEGE

        elif 'Partner with Soulblade' in oracle_text:
            return PartnerType.PARTNER_WITH_SOULBLADE

        elif 'Partner with Lore Weaver' in oracle_text:
            return PartnerType.PARTNER_WITH_WEAVER
        elif 'Partner with Ley Weaver' in oracle_text:
            return PartnerType.PARTNER_WITH_WEAVER
        
        raise CantParseCardError(f'Unknown PARTNER_WITH_*: "{oracle_text}"')
