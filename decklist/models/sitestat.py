from django.db import models


class SiteStat(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    legal_decks = models.IntegerField()

    class Meta:
        get_latest_by = 'timestamp'

    def __str__(self):
        return f"{self.timestamp}: {self.legal_decks} decks"
