import uuid
import functools
import operator
from django.db import models
from django.db.models import Q, F, Count, Window
from django.db.models.functions import Rank
from .card import Card
from .partnertype import PartnerType


class CommanderQuerySet(models.QuerySet):
    def legal_decks(self):
        return self.filter(decks__pdh_legal=True)

    def pairs_for_card(self, card: Card):
        return (
            self
            .filter(Q(commander1=card) | Q(commander2=card))
            .exclude(commander1=card, commander2=None)
            .annotate(count=Count('decks'))
            .order_by('-count')
        )
    
    def top(self):
        return (
            self
            .legal_decks()
            .count_and_rank_decks()
        )

    def decks_of_exact_color(self, w, u, b, r, g):
        wubrg = {
            'w': w,
            'u': u,
            'b': b,
            'r': r,
            'g': g,
        }
        filters = []
        # for each color...
        for c in 'wubrg':
            cmdr1 = f'commander1__identity_{c}'
            cmdr2 = f'commander2__identity_{c}'
            # ... if we want the color, either partner can bring it
            if wubrg[c]:
                filters.append(Q(**dict([(cmdr1,True),])) | Q(**dict([(cmdr2,True),])))
            # ... if we don't want the color, neither partner can bring it
            # ... or else partner2 can be empty
            else:
                filters.append(
                    Q(**dict([(cmdr1,False),])) & 
                    (Q(commander2__isnull=True) | Q(**dict([(cmdr2,False),])))
                )
        
        return (
            self
            .legal_decks()
            .filter(*filters)
        )

    def decks_of_at_least_color(self, w, u, b, r, g):
        # for colorless, it's all legal decks
        if not any([w, u, b, r, g]):
            return self.legal_decks()

        # build up a filter for the aggregation
        # that has a Q object set to True for each color we
        # care about and nothing for the colors which we don't
        wubrg = {
            'w': w,
            'u': u,
            'b': b,
            'r': r,
            'g': g,
        }
        filters = []
        for c in 'wubrg':
            if wubrg[c]:
                cmdr1 = f'commander1__identity_{c}'
                cmdr2 = f'commander2__identity_{c}'
                filters.append(Q(**dict([(cmdr1,True),])) | Q(**dict([(cmdr2,True),])))
        filters = functools.reduce(operator.and_, filters)

        return (
            self
            .legal_decks()
            .filter(filters)
        )
    
    def count_and_rank_decks(self):
        return (
            self
            .annotate(num_decks=Count('decks'))
            .annotate(rank=Window(
                expression=Rank(),
                order_by=F('num_decks').desc(),
            ))
        )

    def partner_pairs(self):
        all_parters = [
            PartnerType.PARTNER,
            PartnerType.PARTNER_WITH_BLARING,
            PartnerType.PARTNER_WITH_CHAKRAM,
            PartnerType.PARTNER_WITH_PROTEGE,
            PartnerType.PARTNER_WITH_SOULBLADE,
            PartnerType.PARTNER_WITH_WEAVER,
        ]

        return (
            self
            .legal_decks()
            .filter(
                Q(commander1__partner_type__in=all_parters)
                | Q(commander2__partner_type__in=all_parters)
            )
            .annotate(num_decks=Count('decks'))
            .annotate(rank=Window(
                expression=Rank(),
                order_by=F('num_decks').desc(),
            ))
        )
    
    def background_pairs(self):
        return (
            self
            .legal_decks()
            .filter(
                Q(commander1__partner_type=PartnerType.BACKGROUND)
                | Q(commander2__partner_type=PartnerType.BACKGROUND)
            )
            .annotate(num_decks=Count('decks'))
            .annotate(rank=Window(
                expression=Rank(),
                order_by=F('num_decks').desc(),
            ))
        )


class Commander(models.Model):
    objects = CommanderQuerySet.as_manager()

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
    # sfid = SmallFormats identifier
    sfid = models.UUIDField(unique=True, verbose_name='SmallFormats ID')

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
            if self.commander1.partner_type == PartnerType.BACKGROUND:
                # for display, always try to put a Background second
                return f"{self.commander2.name} + {self.commander1.name}"
            return f"{self.commander1.name} + {self.commander2.name}"
        return self.commander1.name
    
    def save(self, *args, **kwargs):
        if not self.sfid:
            self.sfid = self._compute_sfid()
        super().save(*args, **kwargs)

    def clean(self):
        # try to move the lower card ID to the commander1 slot
        if self.commander2 and self.commander1.id > self.commander2.id:
            self.commander2, self.commander1 = self.commander1, self.commander2
        # compute the SFID
        self.sfid = self._compute_sfid()

    def _compute_sfid(self):
        namespace = self.commander1.id
        name = str(self.commander2.id) if self.commander2 else ''
        return uuid.uuid5(namespace, name)

    @property
    def color_identity(self):
        identity = [
            x for x in "wubrg"
            if getattr(self.commander1, f"identity_{x}") or (self.commander2 and getattr(self.commander2, f"identity_{x}"))
        ]
        return ''.join(identity).upper() if identity else 'C'
