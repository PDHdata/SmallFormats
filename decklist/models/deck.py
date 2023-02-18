import operator
import functools
from django.db import models
from django.db.models import Q, Count
from django.utils import timezone
from .datasource import DataSource
from .partnertype import PartnerType
from .rarity import Rarity


class DeckQuerySet(models.QuerySet):
    def legal(self):
        return self.filter(pdh_legal=True)


class Deck(models.Model):
    objects = DeckQuerySet.as_manager()

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
        indexes = (
            models.Index(fields=('pdh_legal',)),
        )

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

        # deck has a plausible number of commanders, all commanders printed at
        # uncommon, each have correct types, and partnership is legal
        match list(self.commander_cards()):
            case (commander1,):
                if not commander1.card.ever_uncommon:
                    return False, f"commander {commander1.card.name} not printed at uncommon"
                if not 'Creature' in commander1.card.type_line:
                    return False, f"commander {commander1.card.name} is not a creature"
            
            case (commander1, commander2):
                if not commander1.card.ever_uncommon:
                    return False, f"commander {commander1.card.name} not printed at uncommon"
                if not commander2.card.ever_uncommon:
                    return False, f"commander {commander2.card.name} not printed at uncommon"
                if not ('Creature' in commander1.card.type_line or 'Creature' in commander2.card.type_line):
                    return False, f"at least one commander must be a creature"
                
                match (commander1.card.partner_type, commander2.card.partner_type):
                    case (PartnerType.PARTNER, PartnerType.PARTNER):
                        # both are standard partners
                        pass
                    case ((PartnerType.CHOOSE_A_BACKGROUND, PartnerType.BACKGROUND)
                        | (PartnerType.BACKGROUND, PartnerType.CHOOSE_A_BACKGROUND)):
                        # background and choose-a-background
                        pass
                    case ((PartnerType.PARTNER_WITH_BLARING, PartnerType.PARTNER_WITH_BLARING)
                        | (PartnerType.PARTNER_WITH_CHAKRAM, PartnerType.PARTNER_WITH_CHAKRAM)
                        | (PartnerType.PARTNER_WITH_PROTEGE, PartnerType.PARTNER_WITH_PROTEGE)
                        | (PartnerType.PARTNER_WITH_SOULBLADE, PartnerType.PARTNER_WITH_SOULBLADE)
                        | (PartnerType.PARTNER_WITH_WEAVER, PartnerType.PARTNER_WITH_WEAVER)):
                        # compatible partnerships, as long as they're different
                        if commander1.card.id == commander2.card.id:
                            return False, f'invalid partnership: two copies of "{commander1.card}"'
                    case _:
                        return False, f'invalid partnership: "{commander1.card}" and "{commander2.card}"'
            
            case (commander1, commander2, *_):
                return False, f"{len(self.commander_cards())} is too many commanders"
            
            case _:
                return False, "no commander"

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
                filter=Q(card__printings__rarity=Rarity.COMMON)
            ))
            .filter(common_count=0)
            .count()
        )
        if noncommon_count > 0:
            return False, "non-commander not printed at common"

        return True, None
