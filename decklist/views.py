from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseNotAllowed, Http404, HttpResponsePermanentRedirect
from django.urls import reverse
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.cache import cache_page
from django.utils import timezone
from django.conf import settings
from decklist.models import Card, Deck, Printing, CardInDeck, SiteStat, Commander, Theme, ThemeResult, SynergyScore
from .wubrg_utils import COLORS, filter_to_name, name_to_symbol
from .synergy import compute_synergy
from django_htmx.http import trigger_client_event, HttpResponseClientRefresh
import functools


FRONT_PAGE_TOP_COMMANDERS_TO_ROTATE = 25


@functools.lru_cache(maxsize=2)
def _get_face_card(index):
    try:
        top_cmdr = Commander.objects.top()[index]
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
    cmdrs = Commander.objects.top()
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


def partner_commanders(request):
    return _partner_boilerplate(
        request,
        'Partner',
        Commander.objects.partner_pairs(),
    )


def background_commanders(request):
    return _partner_boilerplate(
        request,
        'Background',
        Commander.objects.background_pairs(),
    )


def _partner_boilerplate(request, heading, partner_queryset):
    paginator = Paginator(partner_queryset, 25, orphans=3)
    page_number = request.GET.get('page')
    cmdrs_page = paginator.get_page(page_number)

    deck_count = Deck.objects.filter(pdh_legal=True).count()

    return render(
        request,
        "stats/commanders.html",
        context={
            'heading': heading,
            'commanders': cmdrs_page,
            'deck_count': deck_count,
        },
    )


def commanders_by_color(request, w=False, u=False, b=False, r=False, g=False):
    cmdrs = (
        Commander.objects
        .decks_of_exact_color(w, u, b, r, g)
        .count_and_rank_decks()
    )
    paginator = Paginator(cmdrs, 25, orphans=3)
    page_number = request.GET.get('page')
    cmdrs_page = paginator.get_page(page_number)

    deck_count = (
        Commander.objects
        .decks_of_exact_color(w, u, b, r, g)
        .count()
    )

    return render(
        request,
        "stats/commanders.html",
        context={
            'heading': filter_to_name({'W':w,'U':u,'B':b,'R':r,'G':g}),
            'commanders': cmdrs_page,
            'deck_count': deck_count,
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
    land_cards = Card.objects.top_lands()
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
        .lands_by_color(w, u, b, r, g)
        .count_and_rank_decks()
    )
    paginator = Paginator(land_cards, 25, orphans=3)
    page_number = request.GET.get('page')
    cards_page = paginator.get_page(page_number)

    deck_count = (
        Commander.objects
        .decks_of_at_least_color(w, u, b, r, g)
        .count()
    )

    return render(
        request,
        "stats/lands.html",
        context={
            'heading': filter_to_name({'W':w,'U':u,'B':b,'R':r,'G':g}),
            'cards': cards_page,
            'deck_count': deck_count,
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
        cards = Card.objects.top()
    else:
        cards = Card.objects.top_nonlands()

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
        .cards_by_color(w, u, b, r, g)
        .count_and_rank_decks()
    )
    paginator = Paginator(cards, 25, orphans=3)
    page_number = request.GET.get('page')
    cards_page = paginator.get_page(page_number)

    deck_count = (
        Commander.objects
        .decks_of_at_least_color(w, u, b, r, g)
        .count()
    )

    return render(
        request,
        "stats/cards.html",
        context={
            'heading': filter_to_name({'W':w,'U':u,'B':b,'R':r,'G':g}),
            'cards': cards_page,
            'deck_count': deck_count,
        },
    )


def theme_index(request, limit_to=None):
    themes = Theme.objects.order_by('display_name')
    if limit_to in (Theme.Type.TRIBE, Theme.Type.KEYWORD):
        themes = themes.filter(filter_type=limit_to)
    else:
        limit_to = None

    return render(
        request,
        'themes/index.html',
        context={
            'themes': themes,
            'kind': limit_to.label if limit_to else None,
            'kinds': Theme.Type,
        }
    )


def single_theme_redirect(request, theme_slug):
    return HttpResponsePermanentRedirect(reverse('theme-single', kwargs={'theme_slug': theme_slug}))

def single_theme(request, theme_slug):
    theme = get_object_or_404(Theme, slug=theme_slug)

    results = (
        ThemeResult.objects
        .for_theme(theme)
    )

    return render(
        request,
        'themes/single.html',
        context={
            'theme': theme.display_name,
            'kind': theme.get_filter_type_display(),
            'word_themed': 'tribal' if theme.filter_type == Theme.Type.TRIBE else 'themed',
            'card_threshold': theme.card_threshold,
            'deck_threshold': theme.deck_threshold,
            'results': results,
        }
    )


def single_card(request, card_id, sort_by_synergy=False):
    card = get_object_or_404(Card, pk=card_id)

    could_be_in = (
        Commander.objects
        .decks_of_at_least_color(
            card.identity_w,
            card.identity_u,
            card.identity_b,
            card.identity_r,
            card.identity_g,
        )
        .count()
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
        .solo_card(card)
    )

    commands = (
        Commander.objects
        .pairs_for_card(card)
    )

    cmdrs = (
        Commander.objects
        .for_card_in_99(card)
        .order_by('-count', '-synergy')
    )
    if sort_by_synergy:
        # from Django 4.1 docs:
        # "Each order_by() call will clear any previous ordering."
        cmdrs = cmdrs.order_by('-synergy', '-count')

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
            'sorted_by_synergy': sort_by_synergy,
        },
    )


def single_card_pairings(request, card_id):
    card = get_object_or_404(Card, pk=card_id)

    pairs = Commander.objects.pairs_for_card(card)

    paginator = Paginator(pairs, 25, orphans=3)
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

    could_be_in = (
        Commander.objects
        .decks_of_at_least_color(**identity)
        .count()
    )

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
        "stats/single_cmdr_decklist.html",
        context={
            'cmdr': cmdr,
            'commander1': cmdr.commander1,
            'commander2': cmdr.commander2,
            'is_pair': cmdr.commander2 is not None,
            'decks': cmdrs_page,
        },
    )


def single_cmdr_synergy(request, cmdr_id):
    commander = get_object_or_404(Commander, sfid=cmdr_id)

    scores = SynergyScore.objects.for_commander(commander).ranked()

    paginator = Paginator(scores, 25, orphans=3)
    page_number = request.GET.get('page')
    scores_page = paginator.get_page(page_number)

    return render(
        request,
        'stats/single_cmdr_synergy.html',
        context={
            'cmdr': commander,
            'scores': scores_page,
            'is_pair': commander.commander2 is not None,
        }
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
        .common_cards(cmdr, filter_to)
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


def synergy(request, cmdr_id, card_id):
    # Calculating synergy is compute-intensive, we do it during
    # nightly crawl in production. This page is sometimes useful
    # in debug mode, though.
    if not settings.DEBUG:
        raise Http404()

    commander = get_object_or_404(Commander, sfid=cmdr_id)
    card = get_object_or_404(Card, pk=card_id)

    synergy = compute_synergy(commander, card)

    return render(
        request,
        'stats/synergy.html',
        context={
            'commander': commander,
            'card': card,
            'synergy': synergy,
        },
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

    results = Card.objects.search(query)

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
