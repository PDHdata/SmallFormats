import operator
import functools
import datetime
from django.db import models
from django.db.models import Q, Count
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    pass


class DataSource(models.IntegerChoices):
    UNKNOWN_OTHER = 0, "Unknown/other"
    ARCHIDEKT = 1
    MOXFIELD = 2


class PartnerType(models.IntegerChoices):
    NONE = 0
    PARTNER = 1, "keyword Partner"
    CHOOSE_A_BACKGROUND = 10, "choose a Background"
    BACKGROUND = 11
    # the BBD partner-with pairs
    PARTNER_WITH_BLARING = 100, "Blaring Captain/Recruiter"
    PARTNER_WITH_CHAKRAM = 101, "Chakram Retriever/Slinger"
    PARTNER_WITH_PROTEGE = 102, "Impetuous Protege/Proud Mentor"
    PARTNER_WITH_SOULBLADE = 103, "Soulblade Corrupter/Renewer"
    PARTNER_WITH_WEAVER = 104, "Ley/Lore Weaver"


class Deck(models.Model):
    name = models.CharField(max_length=100)
    source = models.IntegerField(choices=DataSource.choices)
    source_id = models.CharField(max_length=30, blank=True)
    source_link = models.URLField(blank=True)
    creator_display_name = models.CharField(max_length=50, blank=True)
    ingested_time = models.DateTimeField(auto_now_add=True)
    updated_time = models.DateTimeField(default=timezone.now)

    # these fields are computed, not canonical data
    pdh_legal = models.BooleanField(default=False, verbose_name='is PDH-legal')
    commander = models.ForeignKey(
        'Commander',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='decks',
    )

    def __str__(self):
        return self.name
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('source', 'source_id'),
                name='one_entry_per_deck',
            ),
        ]

    def commander_cards(self):
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
        
        # check the ban list
        if (
            self.card_list
            .filter(
                # PDH ban list
                Q(card__name='Mystic Remora')
                | Q(card__name='Rhystic Study')
                # not strictly banned, but not allowed as commander
                # and never printed at common
                | Q(card__name='Dryad Arbor')
                # WotC inclusiveness bans ever printed at C or U
                | Q(card__name='Pradesh Gypsies')
                | Q(card__name='Stone-Throwing Devils')
            )
            .count()
        ) > 0:
            return False, "contains banned card"

        cmdr_count = self.commander_cards().count()

        # deck has a commander
        if cmdr_count < 1:
            return False, "no commander"
        
        # deck has a plausible number of commanders
        if cmdr_count > 2:
            return False, f"{cmdr_count} is too many commanders"
            
        # all commanders printed at uncommon and have correct types
        for entry in self.commander_cards():
            if not entry.card.ever_uncommon:
                return False, f"commander {entry.card.name} not printed at uncommon"
            if not 'Creature' in entry.card.type_line and not 'Background' in entry.card.type_line:
                return False, f"commander {entry.card.name} is neither Creature nor Background"

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
    partner_type = models.IntegerField(
        choices=PartnerType.choices,
        default=PartnerType.NONE,
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
        
        return (
            self.printings
            # this property is mostly used for image-related things,
            # so let's try to find a printing with a picture
            .exclude(image_uri='')
            .order_by(
                # https://code.djangoproject.com/ticket/19726#comment:8
                # False orders first, and we want True for both of these
                '-is_highres',
                '-is_paper',
                # let's get the newest printing
                '-release_date',
            )
            .first()
        )


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
    is_highres = models.BooleanField(default=True)
    is_paper = models.BooleanField(default=False)
    release_date = models.DateField(default=datetime.date(1993, 8, 5))

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


class SiteStat(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    legal_decks = models.IntegerField()

    class Meta:
        get_latest_by = 'timestamp'

    def __str__(self):
        return f"{self.timestamp}: {self.legal_decks} decks"


class Commander(models.Model):
    commander1 = models.ForeignKey(
        Card,
        on_delete=models.PROTECT,
        related_name='commander1_slots',
    )
    commander2 = models.ForeignKey(
        Card,
        on_delete=models.PROTECT,
        related_name='commander2_slots',
        blank=True,
        null=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['commander1', 'commander2'],
                name='unique_pair_of_commanders',
                condition=Q(commander2__isnull=False),
                violation_error_message='Commander pair is not unique',
            ),
            models.UniqueConstraint(
                fields=['commander1'],
                name='unique_single_commander',
                condition=Q(commander2__isnull=True),
                violation_error_message='Solo commander is not unique',
            ),
            models.CheckConstraint(
                check=(
                    Q(commander1_id__lte=models.F('commander2_id'))
                    | Q(commander2__isnull=True)
                ),
                name='commander1_sorts_before_commander2',
                violation_error_message='Commander 1 ID must sort before commander 2 ID',
            ),
        ]
    
    def __str__(self):
        if self.commander2:
            return f"{self.commander1.name} + {self.commander2.name}"
        return self.commander1.name

    def clean(self):
        # try to move the lower card ID to the commander1 slot
        if self.commander2 and self.commander1.id > self.commander2.id:
            self.commander2, self.commander1 = self.commander1, self.commander2

    @property
    def color_identity(self):
        identity = [
            x for x in "wubrg"
            if getattr(self.commander1, f"identity_{x}") or (self.commander2 and getattr(self.commander2, f"identity_{x}"))
        ]
        return ''.join(identity).upper() if identity else 'C'
