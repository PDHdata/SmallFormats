from django.db import models
from .partnertype import PartnerType
from .rarity import Rarity


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
