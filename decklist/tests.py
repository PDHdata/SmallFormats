from uuid import UUID, uuid4
from warnings import filterwarnings
from django.core.paginator import UnorderedObjectListWarning
from django.test import TestCase, Client
from .models import SynergyScore, Card, Commander, Deck, CardInDeck


class SynergyForCommanderTestCase(TestCase):
    TATYOVA_CARD = UUID('0715e860-3b3b-4331-9718-207973e94fee')
    WALKER_CARD = UUID('fb818376-6e87-4aa3-a050-4b5f82942593')
    LLANOWAR_CARD = UUID('3bdc9211-8eff-4b30-8d6f-d26f4087f77f')
    ATLAS_CARD = UUID('855a4837-7fc8-4b97-afbd-daa88e322c89')

    TATYOVA_CMDR = UUID('f275195d-2a17-5cd3-bdc4-318709b25b0d')
    WALKER_CMDR = UUID('d9c125e4-2cdd-5d40-8221-7dac1eb2dd7c')

    @classmethod
    def setUpTestData(self):
        tatyova_card = Card.objects.create(
            id=SynergyForCommanderTestCase.TATYOVA_CARD,
            name='Tatyova, Benthic Druid',
            identity_u=True,
            identity_g=True,
            type_line='Legendary Creature — Merfolk Druid',
            scryfall_uri='https://scryfall.com/card/dmr/371/tatyova-benthic-druid?utm_source=api',
        )
        tatyova_cmdr = Commander.objects.create(
            commander1=tatyova_card,
        )
        walker_card = Card.objects.create(
            id=SynergyForCommanderTestCase.WALKER_CARD,
            name='Walker of the Wastes',
            type_line='Creature — Eldrazi',
            scryfall_uri='https://scryfall.com/card/ogw/10/walker-of-the-wastes?utm_source=api',
        )
        walker_cmdr = Commander.objects.create(
            commander1=walker_card,
        )
        llanowar_card = Card.objects.create(
            id=SynergyForCommanderTestCase.LLANOWAR_CARD,
            name='Llanowar Scout',
            identity_g=True,
            type_line='Creature — Elf Scout',
            scryfall_uri='https://scryfall.com/card/dom/170/llanowar-scout?utm_source=api',
        )
        atlas_card = Card.objects.create(
            id=SynergyForCommanderTestCase.ATLAS_CARD,
            name='Walking Atlas',
            type_line='Artifact Creature — Construct',
            scryfall_uri='https://scryfall.com/card/wwk/131/walking-atlas?utm_source=api',
        )
        SynergyScore.objects.create(
            commander=tatyova_cmdr,
            card=llanowar_card,
            score=1.0,
        )
        SynergyScore.objects.create(
            commander=tatyova_cmdr,
            card=atlas_card,
            score=0.5,
        )
        SynergyScore.objects.create(
            commander=walker_cmdr,
            card=atlas_card,
            score=0.8,
        )
    
    def setUp(self):
        # Django (as of 4.1) doesn't recognize that adding a Rank expression
        # with an order_by will order the results. This clutters the test
        # results with an unnecessary warning.
        filterwarnings("ignore", category=UnorderedObjectListWarning)
    
    def test_commander_synergy_tatyova(self):
        c = Client()
        response = c.get(f'/cmdr/{SynergyForCommanderTestCase.TATYOVA_CMDR}/synergy')
        scores = response.context['scores']
        self.assertEqual(len(scores), 2)
        self.assertEqual(scores[0].card.id, SynergyForCommanderTestCase.LLANOWAR_CARD)
        self.assertEqual(scores[1].card.id, SynergyForCommanderTestCase.ATLAS_CARD)
    
    def test_commander_synergy_walker(self):
        c = Client()
        response = c.get(f'/cmdr/{SynergyForCommanderTestCase.WALKER_CMDR}/synergy')
        scores = response.context['scores']
        self.assertEqual(len(scores), 1)
        self.assertEqual(scores[0].card.id, SynergyForCommanderTestCase.ATLAS_CARD)


# We have several materialized views which are only used on Postgres.
# Since they have to be updated manually, we should watch for changes
# to the query they're generated from.
class EnsureTopCardViewsMatchQueryTestCase(TestCase):
    @classmethod
    def setUpTestData(self):
        card1 = Card.objects.create(
            id=uuid4(),
            name='Some Card',
            type_line='Artifact',
            scryfall_uri='https://example.com/',
        )
        card2 = Card.objects.create(
            id=uuid4(),
            name='Some Other Card',
            type_line='Land',
            scryfall_uri='https://example.com/',
        )
        deck = Deck.objects.create(
            name='A Deck',
            source=0, # unknown/other
            pdh_legal=True,
        )
        CardInDeck.objects.create(
            card=card1,
            deck=deck,
        )
        CardInDeck.objects.create(
            card=card2,
            deck=deck,
        )

    def _test_qs(self, qs):
        self.assertEqual(
            type(qs).__name__,
            'CardQuerySet',
            'expected to get the real CardQuerySet object for testing',
        )        
        values = qs.values()[0]

        # now we're going to walk the fields of Card, popping them out
        missing = object()
        for f in iter(Card._meta.concrete_fields):
            trial = values.pop(f.name, missing)
            if trial is not missing:
                continue

            # might be a relational key, check for _id version before bailing
            trial = values.pop(f"{f.name}_id")
            self.assertIsNot(trial, missing, f"missing required field {f.name}")
        
        # now we check the annotations that queries like Card.objects.top()
        # are known to add to ensure they're here
        for extra in ['num_decks', 'rank']:
            self.assertIn(extra, values, f"missing required field {extra}")
            values.pop(extra)
        
        # finally, the dictionary should be empty by this point
        self.assertDictEqual({}, values, "query has additional keys left")

    def test_top_card_qs(self):
        # SELECT "decklist_card"."id", "decklist_card"."name", "decklist_card"."identity_w", "decklist_card"."identity_u", "decklist_card"."identity_b", "decklist_card"."identity_r", "decklist_card"."identity_g", "decklist_card"."type_line", "decklist_card"."keywords", "decklist_card"."scryfall_uri", "decklist_card"."editorial_printing_id", "decklist_card"."partner_type", COUNT(DISTINCT "decklist_cardindeck"."id") FILTER (WHERE "decklist_deck"."pdh_legal") AS "num_decks", RANK() OVER (ORDER BY COUNT(DISTINCT "decklist_cardindeck"."id") FILTER (WHERE "decklist_deck"."pdh_legal") DESC) AS "rank" FROM "decklist_card" LEFT OUTER JOIN "decklist_cardindeck" ON ("decklist_card"."id" = "decklist_cardindeck"."card_id") LEFT OUTER JOIN "decklist_deck" ON ("decklist_cardindeck"."deck_id" = "decklist_deck"."id") GROUP BY "decklist_card"."id" HAVING COUNT(DISTINCT "decklist_cardindeck"."id") FILTER (WHERE ("decklist_deck"."pdh_legal")) > 0
        self._test_qs(Card.objects.top())

    def test_top_land_card_qs(self):
        # SELECT "decklist_card"."id", "decklist_card"."name", "decklist_card"."identity_w", "decklist_card"."identity_u", "decklist_card"."identity_b", "decklist_card"."identity_r", "decklist_card"."identity_g", "decklist_card"."type_line", "decklist_card"."keywords", "decklist_card"."scryfall_uri", "decklist_card"."editorial_printing_id", "decklist_card"."partner_type", COUNT(DISTINCT "decklist_cardindeck"."id") FILTER (WHERE "decklist_deck"."pdh_legal") AS "num_decks", RANK() OVER (ORDER BY COUNT(DISTINCT "decklist_cardindeck"."id") FILTER (WHERE "decklist_deck"."pdh_legal") DESC) AS "rank" FROM "decklist_card" LEFT OUTER JOIN "decklist_cardindeck" ON ("decklist_card"."id" = "decklist_cardindeck"."card_id") LEFT OUTER JOIN "decklist_deck" ON ("decklist_cardindeck"."deck_id" = "decklist_deck"."id") WHERE "decklist_card"."type_line"::text LIKE %Land% GROUP BY "decklist_card"."id" HAVING COUNT(DISTINCT "decklist_cardindeck"."id") FILTER (WHERE ("decklist_deck"."pdh_legal")) > 0
        self._test_qs(Card.objects.top_lands())

    def test_top_nonland_card_qs(self):
        # SELECT "decklist_card"."id", "decklist_card"."name", "decklist_card"."identity_w", "decklist_card"."identity_u", "decklist_card"."identity_b", "decklist_card"."identity_r", "decklist_card"."identity_g", "decklist_card"."type_line", "decklist_card"."keywords", "decklist_card"."scryfall_uri", "decklist_card"."editorial_printing_id", "decklist_card"."partner_type", COUNT(DISTINCT "decklist_cardindeck"."id") FILTER (WHERE "decklist_deck"."pdh_legal") AS "num_decks", RANK() OVER (ORDER BY COUNT(DISTINCT "decklist_cardindeck"."id") FILTER (WHERE "decklist_deck"."pdh_legal") DESC) AS "rank" FROM "decklist_card" LEFT OUTER JOIN "decklist_cardindeck" ON ("decklist_card"."id" = "decklist_cardindeck"."card_id") LEFT OUTER JOIN "decklist_deck" ON ("decklist_cardindeck"."deck_id" = "decklist_deck"."id") WHERE NOT ("decklist_card"."type_line"::text LIKE %Land%) GROUP BY "decklist_card"."id" HAVING COUNT(DISTINCT "decklist_cardindeck"."id") FILTER (WHERE ("decklist_deck"."pdh_legal")) > 0
        self._test_qs(Card.objects.top_nonlands())
