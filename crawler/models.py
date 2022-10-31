from django.db import models
from decklist.models import Deck, DataSource


class CrawlRun(models.Model):
    class State(models.IntegerChoices):
        NOT_STARTED = 0
        FETCHING_DECKS = 1
        DONE_FETCHING_DECKS = 2
        FETCHING_DECKLISTS = 3
        DONE_FETCHING_DECKLISTS = 4
        COMPLETE = 5
        
        CANCELLED = 98
        ERROR = 99

    crawl_start_time = models.DateTimeField()
    target = models.IntegerField(choices=DataSource.choices)
    state = models.IntegerField(choices=State.choices)
    note = models.TextField(blank=True)

    def __str__(self):
        return f"Run {self.id} [{self.get_target_display()}] ({self.crawl_start_time})"


class DeckCrawlResult(models.Model):
    url = models.URLField()
    deck = models.ForeignKey(
        Deck,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    # Last update time according to data source"
    updated_time = models.DateTimeField()
    got_cards = models.BooleanField(default=False)
    run = models.ForeignKey(
        CrawlRun,
        on_delete=models.CASCADE,
        related_name='deck_results',
    )

    def __str__(self):
        return f"{self.url}"