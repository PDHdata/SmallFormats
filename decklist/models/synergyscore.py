from django.db import models
from django.db.models import F, Window
from django.db.models.functions import Rank
from .card import Card

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .commander import Commander


class SynergyQuerySet(models.QuerySet):
    def for_commander(self, commander: "Commander"):
        return self.filter(commander=commander)
    
    def ranked(self):
        return self.annotate(rank=Window(
            expression=Rank(),
            order_by=F('score').desc(nulls_last=True),
        ))


class SynergyScore(models.Model):
    objects = SynergyQuerySet.as_manager()

    commander = models.ForeignKey(
        'Commander',
        on_delete=models.CASCADE,
        related_name='synergy_scores',
    )
    card = models.ForeignKey(
        Card,
        on_delete=models.CASCADE,
        related_name='synergy_scores',
    )
    score = models.FloatField(
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['commander', 'card'],
                name='commander_card',
                violation_error_message='Commander + card is not unique',
            ),
        ]

    def __str__(self):
        return f"{self.card} :: {self.commander} ({self.score})"
