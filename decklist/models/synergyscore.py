from django.db import models
from .commander import Commander
from .card import Card


class SynergyScore(models.Model):
    commander = models.ForeignKey(
        Commander,
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
