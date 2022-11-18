import operator
import functools
from django.db import models
from django.db.models import Q, Count
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
    creator_display_name = models.CharField(max_length=50, blank=True)
    ingested_time = models.DateTimeField(auto_now_add=True)
    updated_time = models.DateTimeField(default=timezone.now)
    pdh_legal = models.BooleanField(default=False, verbose_name='is PDH-legal')

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
        return (
            self.card_list
            .filter(is_pdh_commander=True)
            .select_related('card')
        )
    
    def identity(self):
        cmdr_identities = (
            self.card_list
            .filter(is_pdh_commander=True)
            .select_related('card')
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
            .select_related('card')
            .filter(is_pdh_commander=True)
            .filter(card__identity_w=True)
            .count() > 0
        )
    
    def identity_u(self):
        return (
            self.card_list
            .select_related('card')
            .filter(is_pdh_commander=True)
            .filter(card__identity_u=True)
            .count() > 0
        )
    
    def identity_b(self):
        return (
            self.card_list
            .select_related('card')
            .filter(is_pdh_commander=True)
            .filter(card__identity_b=True)
            .count() > 0
        )
    
    def identity_r(self):
        return (
            self.card_list
            .select_related('card')
            .filter(is_pdh_commander=True)
            .filter(card__identity_r=True)
            .count() > 0
        )
    
    def identity_g(self):
        return (
            self.card_list
            .select_related('card')
            .filter(is_pdh_commander=True)
            .filter(card__identity_g=True)
            .count() > 0
        )
    
    def check_deck_legality(self):
        # deck has cards at all
        # (TODO: someday, we'll check for 100 cards)
        if self.card_list.count() == 0:
            return False, "no cards in deck"
        
        # TODO: check the ban list

        # all cards in correct identity
        q_filters = []
        identity = self.identity()

        if all([val for _, val in identity.items()]):
            # 5-color decks exclude no cards
            pass
        else:
            if not identity['white']:
                q_filters.append(Q(card__identity_w=True))
            if not identity['blue']:
                q_filters.append(Q(card__identity_u=True))
            if not identity['black']:
                q_filters.append(Q(card__identity_b=True))
            if not identity['red']:
                q_filters.append(Q(card__identity_r=True))
            if not identity['green']:
                q_filters.append(Q(card__identity_g=True))
            filterset = functools.reduce(operator.or_, q_filters)

            illegal_card_count = (
                self.card_list
                .filter(filterset)
                .count()
            )
            if illegal_card_count > 0:
                return False, f"{illegal_card_count} cards out of color identity"

        # all commanders printed at uncommon
        for entry in self.commanders():
            if not entry.card.ever_uncommon:
                return False, "commander not printed at uncommon"

        # all other cards printed at common
        noncommon_count = (
            self.card_list
            .select_related('card')
            .filter(is_pdh_commander=False)
            .annotate(common_count=Count(
                'card__printings',
                filter=Q(card__printings__rarity=Printing.Rarity.COMMON)
            ))
            .filter(common_count=0)
            .count()
        )
        if noncommon_count > 0:
            return False, "non-commander not printed at common"

        return True, None


class Card(models.Model):
    # this must be the Scryfall oracle ID for the card
    # because we're mostly dealing in abstract cards here.
    id = models.UUIDField(primary_key=True)
    # at this time, "Asmoranomardicadaistinaculdacar" and
    # "Infernal Spawn of Infernal Spawn of Evil" are the longest
    # reasonable card names, at 31/40 characters. Padding to 100
    # to account for split cards in "CardA // CardB" format.
    # Market Research Elemental (not its actual name) will be
    # truncated in the card-data importer.
    name = models.CharField(max_length=100)
    identity_w = models.BooleanField(default=False, verbose_name='is W')
    identity_u = models.BooleanField(default=False, verbose_name='is U')
    identity_b = models.BooleanField(default=False, verbose_name='is B')
    identity_r = models.BooleanField(default=False, verbose_name='is R')
    identity_g = models.BooleanField(default=False, verbose_name='is G')
    # double-sided cards have double-sided type_lines
    type_line = models.CharField(max_length=100)
    scryfall_uri = models.URLField(max_length=200)
    editorial_printing = models.ForeignKey(
        'Printing',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='editorial_showings',
    )

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
    
    @property
    def default_printing(self):
        if self.editorial_printing:
            return self.editorial_printing
        return self.printings.first()


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
    set_code = models.CharField(max_length=10)
    rarity = models.CharField(max_length=1, choices=Rarity.choices)
    image_uri = models.URLField(max_length=200, blank=True)

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
