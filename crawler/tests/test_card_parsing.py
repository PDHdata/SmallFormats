import json
from datetime import date
from pathlib import Path

from django.test import TestCase

from crawler.card_parsing import parse_card_and_printing, FailedToParseCard
from decklist.models import Rarity, PartnerType


class CardParsingTestCase(TestCase):
    def test_easy_card(self):
        with open('crawler/tests/static-orb.json') as f:
            json_obj = json.load(f)
        c, p = parse_card_and_printing(json_obj)
        # card
        self.assertEqual(c.id, "0004ebd0-dfd6-4276-b4a6-de0003e94237")
        self.assertEqual(c.name, "Static Orb")
        self.assertEqual(c.identity_w, False)
        self.assertEqual(c.identity_u, False)
        self.assertEqual(c.identity_b, False)
        self.assertEqual(c.identity_r, False)
        self.assertEqual(c.identity_g, False)
        self.assertEqual(c.type_line, "Artifact")
        self.assertEqual(c.partner_type, PartnerType.NONE)
        # printing
        self.assertEqual(p.id, "86bf43b1-8d4e-4759-bb2d-0b2e03ba7012")
        self.assertEqual(p.set_code, "7ed")
        self.assertEqual(p.rarity, Rarity.RARE)
        self.assertEqual(p.release_date, date(year=2001, month=4, day=11))
    
    def test_verhey_card(self):
        with open('crawler/tests/propaganda-propaganda.json') as f:
            json_obj = json.load(f)
        c, p = parse_card_and_printing(json_obj)
        # card
        self.assertEqual(c.id, "ea9709b6-4c37-4d5a-b04d-cd4c42e4f9dd")
        self.assertEqual(c.name, "Propaganda")
        self.assertEqual(c.identity_w, False)
        self.assertEqual(c.identity_u, True)
        self.assertEqual(c.identity_b, False)
        self.assertEqual(c.identity_r, False)
        self.assertEqual(c.identity_g, False)
        self.assertEqual(c.type_line, "Enchantment")
        self.assertEqual(c.partner_type, PartnerType.NONE)
        # printing
        self.assertEqual(p.id, "3e3f0bcd-0796-494d-bf51-94b33c1671e9")
        self.assertEqual(p.set_code, "sld")
        self.assertEqual(p.rarity, Rarity.RARE)
        self.assertEqual(p.release_date, date(year=2022, month=4, day=22))
    
    def test_partner_card(self):
        with open('crawler/tests/ley-weaver.json') as f:
            json_obj = json.load(f)
        c, p = parse_card_and_printing(json_obj)
        # card
        self.assertEqual(c.id, "24f1f0e9-8c9b-4f32-95ec-7af883bbeef4")
        self.assertEqual(c.name, "Ley Weaver")
        self.assertEqual(c.identity_w, False)
        self.assertEqual(c.identity_u, False)
        self.assertEqual(c.identity_b, False)
        self.assertEqual(c.identity_r, False)
        self.assertEqual(c.identity_g, True)
        self.assertEqual(c.type_line, "Creature — Human Druid")
        self.assertEqual(c.partner_type, PartnerType.PARTNER_WITH_WEAVER)
        # printing
        self.assertEqual(p.id, "2c7e9d68-d419-4ec5-97e9-2478ecb7007f")
        self.assertEqual(p.set_code, "bbd")
        self.assertEqual(p.rarity, Rarity.UNCOMMON)
        self.assertEqual(p.release_date, date(year=2018, month=6, day=8))
    
    def test_non_card(self):
        count = 0
        for bogus in Path('crawler/tests/').glob('_bogus*.json'):
            count = count + 1
            with open(bogus) as f:
                json_obj = json.load(f)
            with self.assertRaises(FailedToParseCard):
                _, _ = parse_card_and_printing(json_obj)
        
        # make sure we found at least one bogus file
        self.assertGreater(count, 0)

    # TODO:
    # test_multicolor_card
    # test_multicolor_identity
    # test_double_face
