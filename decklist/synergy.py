from decklist.models import Commander, Card, Deck
from django.db.models import Count, Q, FloatField
from django.db.models.functions import Cast


def compute_synergy(commander: Commander, card: Card):
    # what fraction of this commander's decks does the card appear in?
    in_percent_commander_decks = (
        Deck.objects
        .filter(pdh_legal=True, commander=commander)
        .aggregate(
            appears_frac=(
                # how many of the commander's decks the card appears in
                Cast(
                    Count(
                        'card_list__card',
                        filter=Q(card_list__card=card) & Q(card_list__is_pdh_commander=False)
                    ),
                    output_field=FloatField()
                )
                /
                # all decks for the commander
                Cast(Count('id', distinct=True), output_field=FloatField())
            ),
        )
    )
    # if there was, for example, division by zero in the database, we want
    # this to end up NaN because the result would be nonsense
    percent_decks = in_percent_commander_decks['appears_frac'] or float('nan')

    # what fraction of decks belonging to other legal commanders for this card
    # does it appear in?
    in_percent_noncommander_decks = (
        Commander.objects
        .decks_of_at_least_color(
            card.identity_w,
            card.identity_u,
            card.identity_b,
            card.identity_r,
            card.identity_g,
        )
        .exclude(id=commander.id)
        .aggregate(
            appears_frac=(
                # how many other-commander decks the card appears in
                Cast(Count('decks', filter=Q(decks__pdh_legal=True) & Q(decks__card_list__card=card), distinct=True), output_field=FloatField())
                /
                # how many total decks for the other commanders
                Cast(Count('decks', filter=Q(decks__pdh_legal=True), distinct=True), output_field=FloatField())
            ),
        )
    )
    # if it appears nowhere else, treat as 0
    percent_other_decks = in_percent_noncommander_decks['appears_frac'] or 0.0

    return round(percent_decks - percent_other_decks, 2)


def compute_synergy_bulk(card: Card) -> list[tuple[Commander, float]]:
    """For daily maintenance, it's faster to compute synergy for a card against
    all commanders at once than going one by one."""
    # calculate this card's appearance in all valid decks once
    in_all_decks = (
        Commander.objects
        .decks_of_at_least_color(
            card.identity_w,
            card.identity_u,
            card.identity_b,
            card.identity_r,
            card.identity_g,
        )
        .exclude(commander1=card)
        .exclude(commander2=card)
        .aggregate(
            appears=Count('decks', filter=Q(decks__pdh_legal=True) & Q(decks__card_list__card=card), distinct=True),
            total=Count('decks', filter=Q(decks__pdh_legal=True), distinct=True),
        )
    )

    if in_all_decks['appears'] == 0:
        return []

    appears = float(in_all_decks['appears'])
    total = float(in_all_decks['total'])

    # then calculate its appearance with each commander
    with_each_commander = (
        Commander.objects
        .decks_of_at_least_color(
            card.identity_w,
            card.identity_u,
            card.identity_b,
            card.identity_r,
            card.identity_g,
        )
        .exclude(commander1=card)
        .exclude(commander2=card)
        .annotate(
            appears=Count('decks', filter=Q(decks__pdh_legal=True) & Q(decks__card_list__card=card), distinct=True),
            total=Count('decks', filter=Q(decks__pdh_legal=True), distinct=True),
        )
        .filter(appears__gt=0)
    )

    # For each commander, the card's synergy is
    #   (appearance with commander) - (all appearances - appearances with commander)
    #
    # Note: this calculation will blow up if total - cmdr.total = 0.
    # That is, if a card appears only with this commander and there are no
    # other legal decks where it could appear. This would imply that there are
    # no decks for any other same-color-identity commanders and no decks for
    # any commander with a broader color identity, which is extremely unlikely.
    # It isn't worth making this code less elegant to deal with a condition
    # which will almost certainly never come up in practice.
    return [
        (cmdr, round(
            (cmdr.appears / cmdr.total) - ((appears - cmdr.appears) / (total - cmdr.total)),
            ndigits=2,
        ))
        for cmdr in with_each_commander
    ]
