from django.db import models
from django.db.models import Count, F, Q, Window
from django.db.models.functions import Rank
from .partnertype import PartnerType
from .rarity import Rarity


class CardQuerySet(models.QuerySet):
    def top_lands(self):
        return (
            self
            .filter(type_line__contains='Land')
            .count_and_rank_decks()
        )
    
    def top_nonlands(self):
        return (
            self
            .exclude(type_line__contains='Land')
            .count_and_rank_decks()
        )
    
    def top(self):
        # this is a synonym for now, but the access pattern
        # might be different in the future
        return self.count_and_rank_decks()
    
    def lands_by_color(self, w: bool, u: bool, b: bool, r: bool, g: bool):
        return (
            self
            .filter(
                type_line__contains='Land',
                identity_w=w,
                identity_u=u,
                identity_b=b,
                identity_r=r,
                identity_g=g,
            )
        )

    def cards_by_color(self, w: bool, u: bool, b: bool, r: bool, g: bool):
        return (
            self
            .filter(
                identity_w=w,
                identity_u=u,
                identity_b=b,
                identity_r=r,
                identity_g=g,
            )
        )

    def count_and_rank_decks(self):
        return (
            self
            .annotate(num_decks=Count(
                'deck_list',
                distinct=True,
                filter=Q(deck_list__deck__pdh_legal=True),
            ))
            .filter(num_decks__gt=0)
            .annotate(rank=Window(
                expression=Rank(),
                order_by=F('num_decks').desc(),
            ))
        )


class Card(models.Model):
    objects = CardQuerySet.as_manager()

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
    keywords = models.JSONField(default=list)
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
            rarity=Rarity.COMMON
        ).count() > 0
    
    @property
    def ever_uncommon(self):
        return self.printings.filter(
            rarity=Rarity.UNCOMMON
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
