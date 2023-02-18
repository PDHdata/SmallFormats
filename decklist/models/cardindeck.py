from django.db import models
from django.db.models import Count, F, Window
from django.db.models.functions import Rank
from .deck import Deck
from .card import Card
from .commander import Commander


class CardInDeckQuerySet(models.QuerySet):
    def common_cards(self, commander: Commander, type_filter: str):
        return (
            self
            .filter(
                is_pdh_commander=False,
                deck__commander=commander,
            )
            .exclude(card__type_line__contains='Basic')
            .filter(card__type_line__contains=type_filter)
            .values('card')
            .annotate(count=Count('deck'))
            .values('count', 'card__id', 'card__name')
            .filter(count__gt=0)
            .annotate(rank=Window(
                expression=Rank(),
                order_by=F('count').desc(),
            ))
        )


class CardInDeck(models.Model):
    objects = CardInDeckQuerySet.as_manager()

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
