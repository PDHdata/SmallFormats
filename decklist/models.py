from django.db import models
from django.db.models import Q
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    pass


class DataSource(models.IntegerChoices):
    UNKNOWN_OTHER = 0, "Unknown/other"
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
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('source', 'source_id'),
                name='one_entry_per_deck',
            ),
        ]

    def commanders(self):
        return self.card_list.filter(is_pdh_commander=True)
    
    def identity(self):
        cmdr_identities = (
            self.card_list.filter(is_pdh_commander=True)
            .aggregate(
                white=models.Count('card', filter=Q(card__identity_w=True)),
                blue= models.Count('card', filter=Q(card__identity_u=True)),
                black=models.Count('card', filter=Q(card__identity_b=True)),
                red=  models.Count('card', filter=Q(card__identity_r=True)),
                green=models.Count('card', filter=Q(card__identity_g=True)),
            )
        )

        return {
            k: v > 0 for k, v in cmdr_identities.items()
        }
    
    def identity_w(self):
        return (
            self.card_list
            .filter(is_pdh_commander=True)
            .filter(card__identity_w=True)
            .count() > 0
        )
    
    def identity_u(self):
        return (
            self.card_list
            .filter(is_pdh_commander=True)
            .filter(card__identity_u=True)
            .count() > 0
        )
    
    def identity_b(self):
        return (
            self.card_list
            .filter(is_pdh_commander=True)
            .filter(card__identity_b=True)
            .count() > 0
        )
    
    def identity_r(self):
        return (
            self.card_list
            .filter(is_pdh_commander=True)
            .filter(card__identity_r=True)
            .count() > 0
        )
    
    def identity_g(self):
        return (
            self.card_list
            .filter(is_pdh_commander=True)
            .filter(card__identity_g=True)
            .count() > 0
        )


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
    type_line = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.name
    
    @property
    def color_identity(self):
        identity = [x for x in "wubrg" if getattr(self, f"identity_{x}")]
        return ''.join(identity).upper() if identity else 'C'
    
    @property
    def ever_common(self):
        return self.printings.filter(
            rarity=Printing.Rarity.COMMON
        ).count() > 0
    
    @property
    def ever_uncommon(self):
        return self.printings.filter(
            rarity=Printing.Rarity.UNCOMMON
        ).count() > 0


class Printing(models.Model):
    class Rarity(models.TextChoices):
        COMMON = 'C', "common"
        UNCOMMON = 'U', "uncommon"
        RARE = 'R', "rare"
        SPECIAL = 'S', "special"
        MYTHIC = 'M', "mythic"
        BONUS = 'B', "bonus"
    # this is the Scryfall ID for the card
    id = models.UUIDField(primary_key=True)
    # we'll link back to the oracle card which has all the info
    card = models.ForeignKey(
        Card,
        on_delete=models.CASCADE,
        related_name='printings',
    )
    set_code = models.CharField(max_length=5, blank=True)
    rarity = models.CharField(max_length=1, choices=Rarity.choices)

    def __str__(self):
        return f"{self.card.name} ({self.set_code})"


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
