# Generated by Django 4.1.3 on 2023-02-18 18:26

from django.db import migrations


# These were created by asking the for str(Card.objects.top().query) and
# friends. They differ per database vendor. Then, the contents of the
# real Card object were replaced with `card_id` by hand. If the shape
# of those top-card queries ever changes, these views will need to be
# mutated as well.
TOP_CARDS_SQL = """
CREATE MATERIALIZED VIEW decklist_topcardview AS
SELECT
  "decklist_card"."id" AS "card_id",
  COUNT(DISTINCT "decklist_cardindeck"."id")
    FILTER (WHERE "decklist_deck"."pdh_legal")
    AS "num_decks",
  RANK() OVER (ORDER BY COUNT(DISTINCT "decklist_cardindeck"."id")
    FILTER (WHERE "decklist_deck"."pdh_legal") DESC)
    AS "rank"
FROM "decklist_card"
LEFT OUTER JOIN "decklist_cardindeck"
  ON ("decklist_card"."id" = "decklist_cardindeck"."card_id")
LEFT OUTER JOIN "decklist_deck"
  ON ("decklist_cardindeck"."deck_id" = "decklist_deck"."id")
GROUP BY "decklist_card"."id"
  HAVING COUNT(DISTINCT "decklist_cardindeck"."id")
  FILTER (WHERE ("decklist_deck"."pdh_legal")) > 0
;
CREATE UNIQUE INDEX decklist_topcardview_pk ON decklist_topcardview(card_id);
"""

TOP_LAND_CARDS_SQL = """
CREATE MATERIALIZED VIEW decklist_toplandcardview AS
SELECT
  "decklist_card"."id" AS "card_id",
  COUNT(DISTINCT "decklist_cardindeck"."id")
    FILTER (WHERE "decklist_deck"."pdh_legal")
    AS "num_decks",
  RANK() OVER (ORDER BY COUNT(DISTINCT "decklist_cardindeck"."id")
    FILTER (WHERE "decklist_deck"."pdh_legal") DESC)
    AS "rank"
FROM "decklist_card"
LEFT OUTER JOIN "decklist_cardindeck"
  ON ("decklist_card"."id" = "decklist_cardindeck"."card_id")
LEFT OUTER JOIN "decklist_deck"
  ON ("decklist_cardindeck"."deck_id" = "decklist_deck"."id")
WHERE "decklist_card"."type_line"::text LIKE \'%Land%\'
GROUP BY "decklist_card"."id"
  HAVING COUNT(DISTINCT "decklist_cardindeck"."id")
  FILTER (WHERE ("decklist_deck"."pdh_legal")) > 0
;
CREATE UNIQUE INDEX decklist_toplandcardview_pk ON decklist_toplandcardview(card_id);
"""

TOP_NON_LAND_CARDS_SQL = """
CREATE MATERIALIZED VIEW decklist_topnonlandcardview AS
SELECT
  "decklist_card"."id" AS "card_id",
  COUNT(DISTINCT "decklist_cardindeck"."id")
    FILTER (WHERE "decklist_deck"."pdh_legal")
    AS "num_decks",
  RANK() OVER (ORDER BY COUNT(DISTINCT "decklist_cardindeck"."id")
    FILTER (WHERE "decklist_deck"."pdh_legal") DESC)
    AS "rank"
FROM "decklist_card"
LEFT OUTER JOIN "decklist_cardindeck"
  ON ("decklist_card"."id" = "decklist_cardindeck"."card_id")
LEFT OUTER JOIN "decklist_deck"
  ON ("decklist_cardindeck"."deck_id" = "decklist_deck"."id")
WHERE NOT ("decklist_card"."type_line"::text LIKE \'%Land%\')
GROUP BY "decklist_card"."id"
  HAVING COUNT(DISTINCT "decklist_cardindeck"."id")
  FILTER (WHERE ("decklist_deck"."pdh_legal")) > 0
;
CREATE UNIQUE INDEX decklist_topnonlandcardview_pk ON decklist_topnonlandcardview(card_id);
"""

DROP_SQL = 'DROP MATERIALIZED VIEW {view_name};'


class Migration(migrations.Migration):

    dependencies = [
        ('decklist', '0022_top_card_models'),
    ]

    operations = [
        migrations.RunSQL(
          TOP_CARDS_SQL,
          DROP_SQL.format(view_name='decklist_topcardview'),
        ),
        migrations.RunSQL(
          TOP_LAND_CARDS_SQL,
          DROP_SQL.format(view_name='decklist_toplandcardview'),
        ),
        migrations.RunSQL(
          TOP_NON_LAND_CARDS_SQL,
          DROP_SQL.format(view_name='decklist_topnonlandcardview'),
        ),
    ]
