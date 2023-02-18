from django.db import models
from django.db.models import F, Window
from django.db.models.functions import Rank
from .theme import Theme
from .commander import Commander


class ThemeResultQuerySet(models.QuerySet):
    def for_theme(self, theme: Theme):
        return (self
            .filter(theme=theme)
            .annotate(rank=Window(
                expression=Rank(),
                order_by=F('theme_deck_count').desc(),
            ))
        )


class ThemeResult(models.Model):
    objects = ThemeResultQuerySet.as_manager()

    theme = models.ForeignKey(
        Theme,
        on_delete=models.CASCADE,
        related_name='results',
    )
    commander = models.ForeignKey(
        Commander,
        on_delete=models.CASCADE,
        related_name='theme_results',
    )
    theme_deck_count = models.IntegerField()
    total_deck_count = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['theme', 'commander'],
                name='theme_commander',
                violation_error_message='Commander + theme is not unique',
            ),
        ]

    def __str__(self):
        return f"{self.theme} for {self.commander}"
