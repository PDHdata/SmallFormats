import uuid
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
