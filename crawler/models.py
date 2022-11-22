from django.db import models
from decklist.models import Deck, DataSource


class CrawlRun(models.Model):
    class State(models.IntegerChoices):
        NOT_STARTED = 0
        FETCHING_DECKS = 1
        COMPLETE = 5
        
        CANCELLED = 98
        ERROR = 99

    crawl_start_time = models.DateTimeField()
    # at the beginning of the run, we'll look for the newest deck
    # update we have from the source. if we see a timestamp older
    # than that, since we search from newest to oldest, we know
    # it's time to stop.
    search_back_to = models.DateTimeField(null=True, blank=True)
    target = models.IntegerField(choices=DataSource.choices)
    state = models.IntegerField(choices=State.choices)
    note = models.TextField(blank=True)
    next_fetch = models.URLField(blank=True)

    def __str__(self):
        return f"Run {self.id} [{self.get_target_display()}] ({self.crawl_start_time})"


class DeckCrawlResult(models.Model):
    url = models.URLField()
    deck = models.ForeignKey(
        Deck,
        on_delete=models.CASCADE,
    )
    target = models.IntegerField(
        choices=DataSource.choices,
        default=DataSource.UNKNOWN_OTHER,
    )
    # Last update time according to data source
    updated_time = models.DateTimeField()
    fetchable = models.BooleanField(default=True)
    got_cards = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.url}"
