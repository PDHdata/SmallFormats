# Typal / theme design

Goal: identify commanders with a high proportion of decks with cards in a theme or type.

Example: a commander might be Elf typal if 20% of its decks have 19+ Elf creatures. (20% and 19 are arbitrary constants which may vary by type/theme. Here they are only examples.)

```python
# a deck is typal if it contains > CARD_THRESHOLD cards of TYPE
typal_decks = (
  Deck.objects
  .annotate(typal_count=Count(
    'card_list',
    filter=Q(card_list__card__type_line__contains=TYPE),
  ))
  .filter(typal_count__gt=CARD_THRESHOLD)
)

# a commander is typal if it has > DECK_THRESHOLD percent of decks
typal_cmdrs = (
  Commander.objects
  .annotate(
    typal_deck_count=Count(
      'decks',
      filter=Q(decks__in=typal_decks),
      unique=True,
    ),
    total_deck_count=Count('decks', unique=True),
  )
  .filter(typal_deck_count__gte=F('total_deck_count') * Value(DECK_THRESHOLD))
  .order_by('-typal_deck_count')
)
```

The same principles apply for keywords (flying, menace, etc.).
