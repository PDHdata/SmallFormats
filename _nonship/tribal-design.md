# Tribal / theme design

Goal: identify commanders with a high proportion of decks with cards in a theme or tribe.

Example: a commander might be Elf tribal if 20% of its decks have 19+ Elf creatures. (20% and 19 are arbitrary constants which may vary by tribe/theme. Here they are only examples.)

```python
# a deck is tribal if it contains > CARD_THRESHOLD cards of TYPE
tribal_decks = (
  Deck.objects
  .annotate(tribal_count=Count(
    'card_list',
    filter=Q(card_list__card__type_line__contains=TYPE),
  ))
  .filter(tribal_count__gt=CARD_THRESHOLD)
)

# a commander is tribal if it has > DECK_THRESHOLD percent of decks
tribal_cmdrs = (
  Commander.objects
  .annotate(
    tribal_deck_count=Count(
      'decks',
      filter=Q(decks__in=tribal_decks),
      unique=True,
    ),
    total_deck_count=Count('decks', unique=True),
  )
  .filter(tribal_deck_count__gte=F('total_deck_count') * Value(DECK_THRESHOLD))
  .order_by('-tribal_deck_count')
)
```

The same principles apply for keywords (flying, menace, etc.).
