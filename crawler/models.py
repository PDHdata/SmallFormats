from io import open_code
from django.db import models
from decklist.models import Deck


class DeckCrawlResult(models.Model):
    crawl_time = models.DateTimeField()
    url = models.URLField()
    deck = models.ForeignKey(
        Deck,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    updated_time = models.DateTimeField()
    got_cards = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.crawl_time} {self.deck}"