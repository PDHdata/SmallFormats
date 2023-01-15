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
                Cast(Count('card_list__card', filter=Q(card_list__card=card)), output_field=FloatField())
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
        commanders_of_identity(
            card.identity_w,
            card.identity_u,
            card.identity_b,
            card.identity_r,
            card.identity_g,
            allow_superset=True,
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


def commanders_of_identity(w, u, b, r, g, allow_superset=False):
    """Find all commanders with a color identity. If allow_superset
    is True, then find all commanders of at least that identity."""
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
        # ... if we don't want to allow the color, neither partner can bring it
        # ... (or partner2 can be empty)
        elif not allow_superset:
            filters.append(
                Q(**dict([(cmdr1,False),])) & 
                (Q(commander2__isnull=True) | Q(**dict([(cmdr2,False),])))
            )

    return (
        Commander.objects
        .filter(decks__pdh_legal=True)
        .filter(*filters)
    )
