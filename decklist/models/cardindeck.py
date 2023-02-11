from django.db import models
from .deck import Deck
from .card import Card


class CardInDeck(models.Model):
    deck = models.ForeignKey(
        Deck,
        on_delete=models.CASCADE,
        related_name='card_list',
    )
    card = models.ForeignKey(
        Card,
        on_delete=models.PROTECT,
        related_name='deck_list',
    )
    is_pdh_commander = models.BooleanField(
        default=False,
        verbose_name='is PDH commander',
    )

    def __str__(self):
        return f"{self.card} in {self.deck}"
    
    class Meta:
        indexes = (
            models.Index(fields=('deck', 'card')),
        )
