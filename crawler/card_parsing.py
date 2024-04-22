from django.utils.dateparse import parse_date

from decklist.models import Card, Printing, PartnerType, Rarity


class ParseFailure(Exception): ...
class FailedToParseCard(Exception): ...


def parse_card_and_printing(json_card):
    parse_failures = {}
    for parse in [_extract_card_and_printing, _extract_verhey_card_and_printing]:
        try:
            c, p = parse(json_card)
        except ParseFailure as e:
            parse_failures[parse.__name__] = str(e)
            # try the next method
            c, p = None, None
        
        if c and p: return c, p

    raise FailedToParseCard(parse_failures)


def _extract_card_and_printing(json_card):
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
        type_line = json_card['type_line']

        if 'oracle_text' in json_card:
            oracle_text = json_card['oracle_text']
        elif 'card_faces' in json_card and 'oracle_text' in json_card['card_faces'][0]:
            oracle_text = json_card['card_faces'][0]['oracle_text']
        else:
            oracle_text = ''

        c.partner_type = _determine_partnership(
            p.rarity, keywords, oracle_text, type_line
        )
            
        return c, p
    except KeyError as ke:
        raise ParseFailure(f"missing keyword {ke}")


def _extract_verhey_card_and_printing(json_card):
    # Gavin Verhey's Commander deck has double-sided reprints of
    # single-sided cards, e.g. https://scryfall.com/card/sld/381/propaganda-propaganda
    if (
            not 'card_faces' in json_card
            or not len(json_card['card_faces']) == 2
            or not 'oracle_id' in json_card['card_faces'][0]):
        raise ParseFailure("this isn't shaped like a Verhey card")

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
            c.partner_type = _determine_partnership(
                p.rarity, keywords, oracle_text, type_line
            )

            return c, p
        except Exception as ex:
            raise ParseFailure() from ex

    raise ParseFailure("card face oracle_ids don't match")


def _determine_partnership(rarity, keywords, oracle_text, type_line):
    # we don't care about non-C/U partners
    if rarity not in (Rarity.COMMON, Rarity.UNCOMMON):
        return PartnerType.NONE

    if 'Partner with' in keywords:
        return _determine_partner_with(oracle_text)
    elif 'Partner' in keywords:
        return PartnerType.PARTNER
    elif 'Choose a Background' in oracle_text:
        return PartnerType.CHOOSE_A_BACKGROUND
    elif 'Background' in type_line:
        return PartnerType.BACKGROUND
    
    return PartnerType.NONE

def _determine_partner_with(oracle_text):
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
    
    raise ParseFailure(f'Has keyword "Partner with", but partner unknown')
