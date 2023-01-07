from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseNotAllowed
from django.urls import reverse
from django.db.models import Count, Q, F, Window, Value
from django.db.models.functions import Rank
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.cache import cache_page
from django.utils import timezone
from decklist.models import Card, Deck, Printing, CardInDeck, PartnerType, SiteStat, Commander, Theme
from .wubrg_utils import COLORS, filter_to_name, name_to_symbol
from django_htmx.http import trigger_client_event, HttpResponseClientRefresh
import operator
import functools


FRONT_PAGE_TOP_COMMANDERS_TO_ROTATE = 25

# HACK: see `single_theme_keyword` below for why this is necessary
from django.db import connections
USE_SQLITE_JSON_HACK = True if connections['default'].vendor == 'sqlite' else False


def _deck_count_exact_color(w, u, b, r, g):
    filters = []
    # for each color...
    for c in 'wubrg':
        cmdr1 = f'commander1__identity_{c}'
        cmdr2 = f'commander2__identity_{c}'
        # ... if we want the color, either partner can bring it
        if locals()[c]:
            filters.append(Q(**dict([(cmdr1,True),])) | Q(**dict([(cmdr2,True),])))
        # ... if we don't want the color, neither partner can bring it
        # ... or else partner2 can be empty
        else:
            filters.append(
                Q(**dict([(cmdr1,False),])) & 
                (Q(commander2__isnull=True) | Q(**dict([(cmdr2,False),])))
            )
    
    return (
        Commander.objects
        .filter(decks__pdh_legal=True)
        .filter(*filters)
        .count()
    )


def _deck_count_at_least_color(w, u, b, r, g):
    if not any([w, u, b, r, g]):
        return Deck.objects.count()

    # build up a filter for the aggregation
    # that has a Q object set to True for each color we
    # care about and nothing for the colors which we don't
    filters = []
    for c in 'wubrg':
        if locals()[c]:
            cmdr1 = f'commander1__identity_{c}'
            cmdr2 = f'commander2__identity_{c}'
            filters.append(Q(**dict([(cmdr1,True),])) | Q(**dict([(cmdr2,True),])))
    filters = functools.reduce(operator.and_, filters)

    return (
        Commander.objects
        .filter(decks__pdh_legal=True)
        .filter(filters)
        .count()
    )


@functools.lru_cache(maxsize=2)
def _get_face_card(index):
    try:
        top_cmdr = (
            Commander.objects
            .filter(decks__pdh_legal=True)
            .annotate(num_decks=Count('decks'))
            .order_by('-num_decks')
        )[index]
    except IndexError:
        top_cmdr = None

    if top_cmdr and top_cmdr.commander1.default_printing:
        if top_cmdr.commander2:
            return (
                top_cmdr.commander1.name,
                top_cmdr.commander1.default_printing.image_uri,
                reverse('card-single-pairings', args=(top_cmdr.commander1.id,)),
            )
        else:
            return (
                top_cmdr.commander1.name,
                top_cmdr.commander1.default_printing.image_uri,
                reverse('cmdr-single', args=(top_cmdr.sfid,)),
            )

    # this happens if we have no cards/printings in the database, or
    # if we're asked for an index that's too large, or if we don't
    # have a printing for a card for some reason
    return (
        "Command Tower",
        "https://cards.scryfall.io/normal/front/b/f/bf5dafb0-4fb1-470d-85ce-88f3ae32340b.jpg?1568580226",
        "https://scryfall.com/search?q=%21%22Command+Tower%22",
    )


def stats_index(request, page="stats/index.html"):
    date_ord = timezone.now().toordinal()
    name, image_uri, link = _get_face_card(date_ord % FRONT_PAGE_TOP_COMMANDERS_TO_ROTATE)
    try:
        stats = SiteStat.objects.latest()
    except SiteStat.DoesNotExist:
        stats = None

    return render(
        request,
        page,
        context={
            'image_uri': image_uri,
            'face_card_name': name,
            'face_card_link': link,
            'stats': stats,
        },
    )


def commander_index(request):
    colors = [
        [(c[0], name_to_symbol(c[0]), f'cmdr-{c[0]}') for c in COLORS if c[1] == 0],
        [(c[0], name_to_symbol(c[0]), f'cmdr-{c[0]}') for c in COLORS if c[1] == 1],
        [(c[0], name_to_symbol(c[0]), f'cmdr-{c[0]}') for c in COLORS if c[1] == 2],
        [(c[0], name_to_symbol(c[0]), f'cmdr-{c[0]}') for c in COLORS if c[1] == 3],
        [(c[0], name_to_symbol(c[0]), f'cmdr-{c[0]}') for c in COLORS if c[1] == 4],
        [(c[0], name_to_symbol(c[0]), f'cmdr-{c[0]}') for c in COLORS if c[1] == 5],
    ]
    return render(
        request,
        "stats/commander_index.html",
        context={
            'colors': colors,
        },
    )


def top_commanders(request):
    cmdrs = (
        Commander.objects
        .filter(decks__pdh_legal=True)
        .annotate(num_decks=Count('decks'))
        .annotate(rank=Window(
            expression=Rank(),
            order_by=F('num_decks').desc(),
        ))
    )
    paginator = Paginator(cmdrs, 25, orphans=3)
    page_number = request.GET.get('page')
    cmdrs_page = paginator.get_page(page_number)

    deck_count = Deck.objects.filter(pdh_legal=True).count()

    return render(
        request,
        "stats/commanders.html",
        context={
            'heading': 'top',
            'commanders': cmdrs_page,
            'deck_count': deck_count,
        },
    )


def background_commanders(request):
    cmdrs = (
        Commander.objects
        .filter(decks__pdh_legal=True)
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
    paginator = Paginator(cmdrs, 25, orphans=3)
    page_number = request.GET.get('page')
    cmdrs_page = paginator.get_page(page_number)

    deck_count = Deck.objects.filter(pdh_legal=True).count()

    return render(
        request,
        "stats/commanders.html",
        context={
            'heading': 'Background',
            'commanders': cmdrs_page,
            'deck_count': deck_count,
        },
    )


def commanders_by_color(request, w=False, u=False, b=False, r=False, g=False):
    filters = []
    # for each color...
    for c in 'wubrg':
        cmdr1 = f'commander1__identity_{c}'
        cmdr2 = f'commander2__identity_{c}'
        # ... if we want the color, either partner can bring it
        if locals()[c]:
            filters.append(Q(**dict([(cmdr1,True),])) | Q(**dict([(cmdr2,True),])))
        # ... if we don't want the color, neither partner can bring it
        # ... or else partner2 can be empty
        else:
            filters.append(
                Q(**dict([(cmdr1,False),])) & 
                (Q(commander2__isnull=True) | Q(**dict([(cmdr2,False),])))
            )

    cmdrs = (
        Commander.objects
        .filter(decks__pdh_legal=True)
        .filter(*filters)
        .annotate(num_decks=Count('decks'))
        .annotate(rank=Window(
            expression=Rank(),
            order_by=F('num_decks').desc(),
        ))
    )
    paginator = Paginator(cmdrs, 25, orphans=3)
    page_number = request.GET.get('page')
    cmdrs_page = paginator.get_page(page_number)

    return render(
        request,
        "stats/commanders.html",
        context={
            'heading': filter_to_name({'W':w,'U':u,'B':b,'R':r,'G':g}),
            'commanders': cmdrs_page,
            'deck_count': _deck_count_exact_color(w, u, b, r, g),
        },
    )


def land_index(request):
    colors = [
        [(c[0], name_to_symbol(c[0]), f'land-{c[0]}') for c in COLORS if c[1] == 0],
        [(c[0], name_to_symbol(c[0]), f'land-{c[0]}') for c in COLORS if c[1] == 1],
        [(c[0], name_to_symbol(c[0]), f'land-{c[0]}') for c in COLORS if c[1] == 2],
        [(c[0], name_to_symbol(c[0]), f'land-{c[0]}') for c in COLORS if c[1] == 3],
        [(c[0], name_to_symbol(c[0]), f'land-{c[0]}') for c in COLORS if c[1] == 4],
        [(c[0], name_to_symbol(c[0]), f'land-{c[0]}') for c in COLORS if c[1] == 5],
    ]
    return render(
        request,
        "stats/land_index.html",
        context={
            'colors': colors,
        },
    )


@cache_page(10 * 60)
def top_lands(request):
    land_cards = (
        Card.objects
        .filter(
            deck_list__deck__pdh_legal=True,
            type_line__contains='Land',
        )
        .annotate(num_decks=Count('deck_list'))
        .filter(num_decks__gt=0)
        .annotate(rank=Window(
            expression=Rank(),
            order_by=F('num_decks').desc(),
        ))
    )
    deck_count = Deck.objects.filter(pdh_legal=True).count()
    paginator = Paginator(land_cards, 25, orphans=3)
    page_number = request.GET.get('page')
    cards_page = paginator.get_page(page_number)

    return render(
        request,
        "stats/lands.html",
        context={
            'heading': 'top',
            'cards': cards_page,
            'deck_count': deck_count,
        },
    )


def lands_by_color(request, w=False, u=False, b=False, r=False, g=False):
    land_cards = (
        Card.objects
        .filter(
            type_line__contains='Land',
            identity_w=w,
            identity_u=u,
            identity_b=b,
            identity_r=r,
            identity_g=g,
        )
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
    paginator = Paginator(land_cards, 25, orphans=3)
    page_number = request.GET.get('page')
    cards_page = paginator.get_page(page_number)

    return render(
        request,
        "stats/lands.html",
        context={
            'heading': filter_to_name({'W':w,'U':u,'B':b,'R':r,'G':g}),
            'cards': cards_page,
            'deck_count': _deck_count_at_least_color(w, u, b, r, g),
        },
    )


def card_index(request):
    colors = [
        [(c[0], name_to_symbol(c[0]), f'card-{c[0]}') for c in COLORS if c[1] == 0],
        [(c[0], name_to_symbol(c[0]), f'card-{c[0]}') for c in COLORS if c[1] == 1],
        [(c[0], name_to_symbol(c[0]), f'card-{c[0]}') for c in COLORS if c[1] == 2],
        [(c[0], name_to_symbol(c[0]), f'card-{c[0]}') for c in COLORS if c[1] == 3],
        [(c[0], name_to_symbol(c[0]), f'card-{c[0]}') for c in COLORS if c[1] == 4],
        [(c[0], name_to_symbol(c[0]), f'card-{c[0]}') for c in COLORS if c[1] == 5],
    ]
    return render(
        request,
        "stats/card_index.html",
        context={
            'colors': colors,
        },
    )


@cache_page(10 * 60)
def top_cards(request, include_land=True):
    if include_land:
        cards = Card.objects
    else:
        cards = Card.objects.exclude(type_line__contains='Land')

    cards = (
        cards
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
    paginator = Paginator(cards, 25, orphans=3)
    page_number = request.GET.get('page')
    cards_page = paginator.get_page(page_number)

    deck_count = Deck.objects.filter(pdh_legal=True).count()

    heading = 'top' if include_land else 'top non-land'

    return render(
        request,
        "stats/cards.html",
        context={
            'heading': heading,
            'cards': cards_page,
            'deck_count': deck_count,
        },
    )


def cards_by_color(request, w=False, u=False, b=False, r=False, g=False):
    cards = (
        Card.objects
        .filter(
            identity_w=w,
            identity_u=u,
            identity_b=b,
            identity_r=r,
            identity_g=g,
        )
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
    paginator = Paginator(cards, 25, orphans=3)
    page_number = request.GET.get('page')
    cards_page = paginator.get_page(page_number)

    return render(
        request,
        "stats/cards.html",
        context={
            'heading': filter_to_name({'W':w,'U':u,'B':b,'R':r,'G':g}),
            'cards': cards_page,
            'deck_count': _deck_count_at_least_color(w, u, b, r, g),
        },
    )


def theme_index(request):
    themes = Theme.objects.order_by('display_name')

    return render(
        request,
        'themes/index.html',
        context={
            'themes': themes,
        }
    )


@cache_page(10 * 60)
def single_theme_tribe(request, theme_slug):
    theme = get_object_or_404(Theme, slug=theme_slug, filter_type=Theme.Type.TRIBE)
    
    tribal_decks = (
        Deck.objects
        .filter(pdh_legal=True)
        .annotate(tribal_count=Count(
            'card_list',
            filter=Q(card_list__card__type_line__contains=theme.filter_text),
        ))
        .filter(tribal_count__gt=theme.card_threshold)
    )

    tribal_cmdrs = (
        Commander.objects
        .annotate(
            tribal_decks=Count(
                'decks',
                filter=Q(decks__in=tribal_decks),
                unique=True,
            ),
            total_deck_count=Count('decks', unique=True),
        )
        .filter(tribal_decks__gt=1)
        .filter(tribal_decks__gte=F('total_deck_count') * Value(theme.deck_threshold / 100.0))
        .annotate(rank=Window(
            expression=Rank(),
            order_by=F('tribal_decks').desc(),
        ))
    )

    return render(
        request,
        'themes/tribal.html',
        context={
            'tribe': theme.display_name,
            'card_threshold': theme.card_threshold,
            'deck_threshold': theme.deck_threshold,
            'commanders': tribal_cmdrs,
        }
    )


@cache_page(10 * 60)
def single_theme_keyword(request, theme_slug):
    theme = get_object_or_404(Theme, slug=theme_slug, filter_type=Theme.Type.KEYWORD)
    
    # HACK: `contains` is not supported on JSONField on SQLite.
    # Because we're only storing a flat array, `regex` is a good
    # enough approximation in this instance.
    if USE_SQLITE_JSON_HACK:
        filter = Q(card_list__card__keywords__regex=rf'"{theme.filter_text}"')
    else:
        filter = Q(card_list__card__keywords__contains=theme.filter_text)

    keyword_decks = (
        Deck.objects
        .filter(pdh_legal=True)
        .annotate(keyword_count=Count(
            'card_list',
            filter=filter,
        ))
        .filter(keyword_count__gt=theme.card_threshold)
    )

    keyword_cmdrs = (
        Commander.objects
        .annotate(
            keyword_decks=Count(
                'decks',
                filter=Q(decks__in=keyword_decks),
                unique=True,
            ),
            total_deck_count=Count('decks', unique=True),
        )
        .filter(keyword_decks__gt=1)
        .filter(keyword_decks__gte=F('total_deck_count') * Value(theme.deck_threshold / 100.0))
        .annotate(rank=Window(
            expression=Rank(),
            order_by=F('keyword_decks').desc(),
        ))
    )

    return render(
        request,
        'themes/keyword.html',
        context={
            'keyword': theme.display_name,
            'card_threshold': theme.card_threshold,
            'deck_threshold': theme.deck_threshold,
            'commanders': keyword_cmdrs,
        }
    )


def single_card(request, card_id):
    card = get_object_or_404(Card, pk=card_id)

    could_be_in = _deck_count_at_least_color(
        card.identity_w,
        card.identity_u,
        card.identity_b,
        card.identity_r,
        card.identity_g
    )

    is_in = (
        Deck.objects
        .filter(
            pdh_legal=True,
            card_list__card=card,
            card_list__is_pdh_commander=False,
        )
    )

    solo_commander = (
        Commander.objects
        .filter(commander1=card, commander2=None)
        .first()
    )

    commands = (
        Commander.objects
        .filter(Q(commander1=card) | Q(commander2=card))
        .exclude(commander1=card, commander2=None)
    )

    cmdrs = (
        Commander.objects
        .filter(
            decks__card_list__card=card,
            decks__card_list__is_pdh_commander=False,
        )
        .annotate(count=Count('decks'))
        .order_by('-count')
    )
    paginator = Paginator(cmdrs, 25, orphans=3)
    page_number = request.GET.get('page')
    cmdrs_page = paginator.get_page(page_number)

    return render(
        request,
        "stats/single_card.html",
        context={
            'card': card,
            'is_in': is_in.count(),
            'solo_commander': solo_commander,
            'all_commander': commands,
            'could_be_in': could_be_in,
            'commanders': cmdrs_page,
        },
    )


def single_card_pairings(request, card_id):
    card = get_object_or_404(Card, pk=card_id)

    commands = (
        Commander.objects
        .filter(Q(commander1=card) | Q(commander2=card))
        .exclude(commander1=card, commander2=None)
        .annotate(count=Count('decks'))
        .order_by('-count')
    )

    paginator = Paginator(commands, 25, orphans=3)
    page_number = request.GET.get('page')
    partners_page = paginator.get_page(page_number)

    return render(
        request,
        "stats/single_card_pairings.html",
        context={
            'card': card,
            'partners': partners_page,
        },
    )


def single_cmdr(request, cmdr_id):
    cmdr = get_object_or_404(Commander, sfid=cmdr_id)

    if cmdr.commander2:
        identity = {
            'w': cmdr.commander1.identity_w | cmdr.commander2.identity_w,
            'u': cmdr.commander1.identity_u | cmdr.commander2.identity_u,
            'b': cmdr.commander1.identity_b | cmdr.commander2.identity_b,
            'r': cmdr.commander1.identity_r | cmdr.commander2.identity_r,
            'g': cmdr.commander1.identity_g | cmdr.commander2.identity_g,
        }
    else:
        identity = {
            'w': cmdr.commander1.identity_w,
            'u': cmdr.commander1.identity_u,
            'b': cmdr.commander1.identity_b,
            'r': cmdr.commander1.identity_r,
            'g': cmdr.commander1.identity_g,
        }

    could_be_in = _deck_count_at_least_color(**identity)

    commands = cmdr.decks.order_by('-updated_time')

    context = {}
    # card type codes, see `hx_common_cards`
    for letter in 'caeisplg':
        if page_number := request.GET.get(letter, default=None):
            try:
                if int(page_number) > 1:
                    context[f'page_{letter}'] = page_number
            except ValueError:
                # user probably munged the URL with something like "?c=foo"
                pass
    
    context.update({
        'cmdr': cmdr,
        'commander1': cmdr.commander1,
        'commander2': cmdr.commander2,
        'is_pair': cmdr.commander2 is not None,
        'commands': commands.count(),
        'top_decks': commands[:4],
        'could_be_in': could_be_in,
    })

    return render(
        request,
        "stats/single_cmdr.html",
        context=context,
    )


def single_cmdr_decklist(request, cmdr_id):
    cmdr = get_object_or_404(Commander, sfid=cmdr_id)

    commands = cmdr.decks.order_by('-updated_time')
    paginator = Paginator(commands, 20, orphans=3)
    page_number = request.GET.get('page')
    cmdrs_page = paginator.get_page(page_number)

    return render(
        request,
        "stats/single_cmdr_decklist_new.html",
        context={
            'cmdr': cmdr,
            'commander1': cmdr.commander1,
            'commander2': cmdr.commander2,
            'is_pair': cmdr.commander2 is not None,
            'decks': cmdrs_page,
        },
    )


def hx_common_cards(request, cmdr_id, card_type, page_number):
    if not request.htmx:
        return HttpResponseNotAllowed("expected HTMX request")
    
    cmdr = get_object_or_404(Commander, pk=cmdr_id)

    commands_count = cmdr.decks.count()

    match card_type:
        case 'c':
            filter_to = 'Creature'
            card_type_plural = 'creatures'
        case 'a':
            filter_to = 'Artifact'
            card_type_plural = 'artifacts'
        case 'e':
            filter_to = 'Enchantment'
            card_type_plural = 'enchantments'
        case 'i':
            filter_to = 'Instant'
            card_type_plural = 'instants'
        case 's':
            filter_to = 'Sorcery'
            card_type_plural = 'sorceries'
        case 'p':
            filter_to = 'Planeswalker'
            card_type_plural = 'planeswalkers'
        case 'l':
            filter_to = 'Land'
            card_type_plural = 'lands'
        case 'g':
            filter_to = 'Legendary'
            card_type_plural = 'legendaries'
        case _:
            return HttpResponseNotAllowed()

    
    common_cards = (
        CardInDeck.objects
        .filter(
            is_pdh_commander=False,
            deck__commander=cmdr,
        )
        .exclude(card__type_line__contains='Basic')
        .filter(card__type_line__contains=filter_to)
        .values('card')
        .annotate(count=Count('deck'))
        .values('count', 'card__id', 'card__name')
        .filter(count__gt=0)
        .annotate(rank=Window(
            expression=Rank(),
            order_by=F('count').desc(),
        ))
    )
    paginator = Paginator(common_cards, 10, orphans=3)
    cards_page = paginator.get_page(page_number)

    response = render(
        request,
        "stats/hx_common_cards.html",
        context={
            'cmdr_id': cmdr.id,
            'card_type': card_type,
            'card_type_plural': card_type_plural,
            'commands': commands_count,
            'common_cards': cards_page,
        },
    )
    
    return trigger_client_event(
        response,
        "page_move",
        {
            'type': card_type,
            'page': page_number,
        },
        after="settle",
    )


@login_required
@require_POST
def set_editorial_image(request, card_id):
    if not request.htmx:
        return HttpResponseNotAllowed("expected HTMX request")

    if not request.user.is_superuser:
        raise HttpResponseNotAllowed()
    
    printing_id = request.POST['printing_id']
    card = get_object_or_404(Card, pk=card_id)
    printing = get_object_or_404(Printing, pk=printing_id)

    if printing.card != card:
        raise HttpResponseNotAllowed("printing must belong to card")

    card.editorial_printing = printing
    card.save()
    
    return HttpResponseClientRefresh()


def search(request):
    query = request.GET.get('q', '')

    results = (
        Card.objects
        .filter(name__icontains=query)
        .annotate(
            in_decks=Count(
                'deck_list',
                filter=Q(deck_list__deck__pdh_legal=True),
            ),
            ninetynine_decks=Count(
                'deck_list',
                filter=Q(deck_list__is_pdh_commander=False)
                     & Q(deck_list__deck__pdh_legal=True),
            ),
            helms_decks=Count(
                'deck_list',
                filter=Q(deck_list__is_pdh_commander=True)
                     & Q(deck_list__deck__pdh_legal=True),
            ),
        )
        .filter(in_decks__gt=0)
        .order_by('-in_decks', 'name')
    )
    paginator = Paginator(results, 25, orphans=3)
    page_number = request.GET.get('page')
    results_page = paginator.get_page(page_number)

    return render(
        request,
        'search/results.html',
        {
            'results': results_page,
            'query': query,
        }
    )
