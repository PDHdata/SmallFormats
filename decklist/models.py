from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    pass


class DataSource(models.IntegerChoices):
    UNKNOWN_OTHER = 0
    ARCHIDEKT = 1


class Deck(models.Model):
    name = models.CharField(max_length=100)
    source = models.IntegerField(choices=DataSource.choices)
    source_id = models.CharField(max_length=20, blank=True)
    source_link = models.URLField(blank=True)
    creator_display_name = models.CharField(max_length=50)
    ingested_time = models.DateTimeField(auto_now_add=True)
    updated_time = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name


class Card(models.Model):
    # this must be the Scryfall oracle ID for the card
    # because we're mostly dealing in abstract cards here.
    id = models.UUIDField(primary_key=True)
    # at this time, "Asmoranomardicadaistinaculdacar" and
    # "Infernal Spawn of Infernal Spawn of Evil" are the
    # longest card names, at 31/40 characters. Padding to 100
    # to account for split cards in "CardA // CardB" format.
    name = models.CharField(max_length=100)
    identity_w = models.BooleanField(default=False, verbose_name='is W')
    identity_u = models.BooleanField(default=False, verbose_name='is U')
    identity_b = models.BooleanField(default=False, verbose_name='is B')
    identity_r = models.BooleanField(default=False, verbose_name='is R')
    identity_g = models.BooleanField(default=False, verbose_name='is G')
    # Pauper EDH only cares if a card was _ever_ printed
    # at a certain rarity, not whether the physical card in your
    # deck is that rarity.
    ever_common = models.BooleanField(default=False)
    ever_uncommon = models.BooleanField(default=False)
    # Pauper EDH expects an uncommon creature at the helm.
    # we'll compute that on ingestion so that if an uncommon
    # planeswalker or other card type ever says "this can be
    # your commander", we'll be ready for it.
    can_be_pdh_commander = models.BooleanField(
        default=False,
        verbose_name='can be PDH commander',
    )

    def __str__(self):
        return self.name


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
