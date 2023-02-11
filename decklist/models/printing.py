import datetime
from django.db import models
from .card import Card
from .rarity import Rarity as CompatRarity


class Printing(models.Model):
    # TODO: break dependence on Printing.Rarity everywhere
    Rarity = CompatRarity

    # this is the Scryfall ID for the card
    id = models.UUIDField(primary_key=True)
    # we'll link back to the oracle card which has all the info
    card = models.ForeignKey(
        Card,
        on_delete=models.CASCADE,
        related_name='printings',
    )
    set_code = models.CharField(max_length=10)
    rarity = models.CharField(max_length=1, choices=Rarity.choices)
    image_uri = models.URLField(max_length=200, blank=True)
    is_highres = models.BooleanField(default=True)
    is_paper = models.BooleanField(default=False)
    release_date = models.DateField(default=datetime.date(1993, 8, 5))

    def __str__(self):
        return f"{self.card.name} ({self.set_code})"
