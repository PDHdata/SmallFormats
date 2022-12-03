from itertools import chain
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.urls import reverse
from django.db import transaction
from django.db.models import Q
from django_htmx.http import HttpResponseClientRefresh, HttpResponseClientRedirect, HTMX_STOP_POLLING
from crawler.models import DeckCrawlResult, CrawlRun, LogEntry
from decklist.models import Deck, Printing, CardInDeck, SiteStat, DataSource
import httpx
from crawler.crawlers import CrawlerExit, HEADERS, format_response_error
from crawler.crawlers import ArchidektCrawler, ARCHIDEKT_API_BASE
from crawler.crawlers import MoxfieldCrawler, MOXFIELD_API_BASE


@login_required
def crawler_index(request):
    runs = CrawlRun.objects.order_by('-crawl_start_time')
    paginator = Paginator(runs, 8, orphans=3)
    page_number = request.GET.get('page')
    runs_page = paginator.get_page(page_number)

    try:
        stats = SiteStat.objects.latest()
    except SiteStat.DoesNotExist:
        stats = None

    pending_results = (
        DeckCrawlResult.objects
        .filter(fetchable=True, got_cards=False)
        .count()
    )

    return render(
        request,
        'crawler/index.html',
        {
            'runs': runs_page,
            'pending_results': pending_results,
            'stats': stats,
        },
    )


@login_required
@require_POST
def new_archidekt_run_hx(request):
    return _new_run_hx(request, DataSource.ARCHIDEKT)

@login_required
@require_POST
def new_moxfield_run_hx(request):
    return _new_run_hx(request, DataSource.MOXFIELD)

def _new_run_hx(request, datasource):
    try:
        latest_deck_update = (
            Deck.objects
            .filter(
                source=datasource,
                updated_time__isnull=False,
            )
            .latest('updated_time')
        ).updated_time
    except Deck.DoesNotExist:
        latest_deck_update = None

    run = CrawlRun(
        state=CrawlRun.State.NOT_STARTED,
        target=datasource,
        crawl_start_time=timezone.now(),
        search_back_to=latest_deck_update,
    )

    run.save()
    return HttpResponseClientRedirect(reverse('crawler:run-detail', args=(run.id,)))


@login_required
def run_detail(request, run_id):
    run = get_object_or_404(CrawlRun, pk=run_id)

    source_str = DataSource(run.target).name.lower()
    return render(
        request,
        'crawler/run_detail.html',
        {
            'run': run,
            'poll_view': f'crawler:run-{source_str}-poll',
            'single_view': f'crawler:run-{source_str}-one',
            'resumable': run.state in (CrawlRun.State.NOT_STARTED, CrawlRun.State.FETCHING_DECKS),
            'errored': run.state == CrawlRun.State.ERROR,
            'allow_search_infinite': run.state == CrawlRun.State.NOT_STARTED and run.search_back_to,
            'can_cancel': run.state not in (CrawlRun.State.CANCELLED, CrawlRun.State.COMPLETE),
        },
    )


@login_required
@require_POST
def run_remove_error_hx(request, run_id):
    run = get_object_or_404(CrawlRun, pk=run_id)

    if run.state == run.State.ERROR:
        if run.next_fetch:
            run.state = run.State.FETCHING_DECKS
        else:
            run.state = run.State.NOT_STARTED
        run.save()
    
    return HttpResponseClientRefresh()


@login_required
@require_POST
def run_remove_limit_hx(request, run_id):
    run = get_object_or_404(CrawlRun, pk=run_id)

    if run.state == run.State.NOT_STARTED:
        run.search_back_to = None
        run.save()
    
    return HttpResponseClientRefresh()


@login_required
@require_POST
def run_cancel_hx(request, run_id):
    run = get_object_or_404(CrawlRun, pk=run_id)

    if run.state != CrawlRun.State.COMPLETE:
        run.state = CrawlRun.State.CANCELLED
        run.save()
    
    return HttpResponseClientRefresh()


@login_required
@require_POST
def run_archidekt_onepage_hx(request, run_id):
    return _onepage_hx(request, ARCHIDEKT_API_BASE, ArchidektCrawler, run_id)

@login_required
@require_POST
def run_moxfield_onepage_hx(request, run_id):
    return _onepage_hx(request, MOXFIELD_API_BASE, MoxfieldCrawler, run_id)

def _onepage_hx(request, api_base, Crawler, run_id):
    run = get_object_or_404(CrawlRun, pk=run_id)

    output = []

    with httpx.Client(
        headers=HEADERS,
        base_url=api_base,
    ) as client:

        crawler = Crawler(
            client,
            run.next_fetch,
            run.search_back_to,
            output.append,
        )

        if run.state == run.State.NOT_STARTED or not run.next_fetch:
            # if next_fetch was None, the crawler will build the initial URL
            run.next_fetch = crawler.url
            run.state = run.State.FETCHING_DECKS
            run.save()

        response_status = 200

        try:
            if crawler.get_next_page():
                run.next_fetch = crawler.url
                output.append("Processed a page.")
                run.save()
            else:
                run.state = CrawlRun.State.COMPLETE
                run.next_fetch = ''
                run.save()
                return HttpResponseClientRefresh()

        except CrawlerExit as e:
            # TODO: check for 429. that's not fatal, it means we need
            # to slow down.
            run.state = CrawlRun.State.ERROR
            run.note = (
                str(e) + "\n" + format_response_error(e.respose) if e.response
                else str(e)
            )
            run.save()
            output.append(run.note)
            response_status = HTMX_STOP_POLLING

        return render(
            request,
            'crawler/_continue.html',
            {
                'output': output,
            },
            status=response_status,
        )


@login_required
def start_archidekt_poll_hx(request, run_id):
    return render(
        request,
        'crawler/_start_crawl_poll.html',
        {
            'crawl_one': 'crawler:run-archidekt-one',
            'run_id': run_id,
        },
    )


@login_required
def start_moxfield_poll_hx(request, run_id):
    return render(
        request,
        'crawler/_start_crawl_poll.html',
        {
            'crawl_one': 'crawler:run-moxfield-one',
            'run_id': run_id,
        },
    )


def _process_architekt_deck(crawl_result, cards, output):
    # resolve printings to cards
    lookup_printings = set()
    for card_json in cards:
        printing_id = card_json['card']['uid']
        lookup_printings.add(printing_id)
    print_id_to_card = {
        str(p.id): p.card
        for p in Printing.objects.filter(id__in=lookup_printings)
    }

    # reuse cards where we can
    # TODO: handle multiple printings of the same card?
    current_cards = {
        c.card.id: c for c in CardInDeck.objects.filter(deck=crawl_result.deck)
    }
    update_cards = []
    new_cards = []

    for card_json in cards:
        printing_id = card_json['card']['uid']
        if printing_id not in print_id_to_card.keys():
            name = card_json['card']['oracleCard']['name']
            edition = card_json['card']['edition']['editioncode']
            output.append(f"could not resolve printing {printing_id}; should be \"{name}\" ({edition})")
            continue
        card_id = print_id_to_card[printing_id].id
        if card_id in current_cards.keys():
            reuse_card = current_cards.pop(card_id)
            reuse_card.is_pdh_commander = "Commander" in card_json['categories']
            update_cards.append(reuse_card)
        else:
            new_cards.append(CardInDeck(
                deck=crawl_result.deck,
                card=print_id_to_card[printing_id],
                is_pdh_commander="Commander" in card_json['categories'],
            ))
    
    with transaction.atomic():
        (
            CardInDeck.objects
            .filter(deck=crawl_result.deck)
            .filter(card__id__in=current_cards.keys())
            .delete()
        )
        CardInDeck.objects.bulk_create(new_cards)
        CardInDeck.objects.bulk_update(update_cards, ['is_pdh_commander'])

    # now see if the deck is legal before completing processing
    crawl_result.deck.pdh_legal, _ = crawl_result.deck.check_deck_legality()

    with transaction.atomic():
        crawl_result.deck.save()
        crawl_result.got_cards = True
        crawl_result.save()


def _process_moxfield_deck(crawl_result, envelope, output):
    # resolve printings to cards
    cards = envelope['mainboard']
    cmdrs = envelope['commanders']

    lookup_printings = set()
    for _, card_json in chain(cards.items(), cmdrs.items()):
        printing_id = card_json['card']['scryfall_id']
        lookup_printings.add(printing_id)
    print_id_to_card = {
        str(p.id): p.card
        for p in Printing.objects.filter(id__in=lookup_printings)
    }

    # reuse cards where we can
    current_cards = {
        c.card.id: c for c in CardInDeck.objects.filter(deck=crawl_result.deck)
    }
    update_cards = []
    new_cards = []

    for card_set, is_commander in ((cards, False), (cmdrs, True)):
        for _, card_json in card_set.items():
            printing_id = card_json['card']['scryfall_id']
            if printing_id not in print_id_to_card.keys():
                name = card_json['card']['name']
                edition = card_json['card']['set']
                output.append(f"could not resolve printing {printing_id}; should be \"{name}\" ({edition})")
                continue
            card_id = print_id_to_card[printing_id].id
            if card_id in current_cards.keys():
                reuse_card = current_cards.pop(card_id)
                reuse_card.is_pdh_commander = is_commander
                update_cards.append(reuse_card)
            else:
                new_cards.append(CardInDeck(
                    deck=crawl_result.deck,
                    card=print_id_to_card[printing_id],
                    is_pdh_commander=is_commander,
                ))
    
    with transaction.atomic():
        (
            CardInDeck.objects
            .filter(deck=crawl_result.deck)
            .filter(card__id__in=current_cards.keys())
            .delete()
        )
        CardInDeck.objects.bulk_create(new_cards)
        CardInDeck.objects.bulk_update(update_cards, ['is_pdh_commander'])

    # now see if the deck is legal before completing processing
    crawl_result.deck.pdh_legal, _ = crawl_result.deck.check_deck_legality()

    with transaction.atomic():
        crawl_result.deck.save()
        crawl_result.got_cards = True
        crawl_result.save()


@login_required
@require_POST
def fetch_deck_hx(request):
    try:
        updatable_deck = (
            DeckCrawlResult.objects
            .filter(fetchable=True, got_cards=False)
            .first()
        )
        if not updatable_deck:
            raise DeckCrawlResult.DoesNotExist()
    except DeckCrawlResult.DoesNotExist:
        return HttpResponseClientRefresh()

    output = []
    response_status = 200

    with httpx.Client(
        headers=HEADERS,
    ) as client:
        response = client.get(updatable_deck.url)
        if 200 <= response.status_code < 300:
            deck_name = updatable_deck.deck.name
            new_deck = True if updatable_deck.deck.card_list.count() == 0 else False
            verb = "Creating" if new_deck else "Updating"
            envelope = response.json()
            if updatable_deck.deck.source == DataSource.ARCHIDEKT:
                output.append(f"{verb} \"{deck_name}\" (Archidekt)")
                _process_architekt_deck(updatable_deck, envelope['cards'], output)
            elif updatable_deck.deck.source == DataSource.MOXFIELD:
                output.append(f"{verb} \"{deck_name}\" (Moxfield)")
                _process_moxfield_deck(updatable_deck, envelope, output)
            else:
                output.append(f"Can't update \"{deck_name}\", unimplemented source")
                updatable_deck.fetchable = False
                updatable_deck.save()
        elif response.status_code in (400, 404):
            # mark deck as unfetchable and carry on
            output.append(f"Got error {response.status_code} for \"{updatable_deck.deck.name}\" ({updatable_deck.url}).")
            updatable_deck.fetchable = False
            updatable_deck.save()
        else:
            output.append(f"Got {response.status_code} from server. ({response.url})")
            response_status = HTMX_STOP_POLLING

    if updatable_deck.got_cards:
        updatable_deck.deck.deckcrawlresult_set.all().delete()

    return render(
        request,
        'crawler/_continue.html',
        {
            'output': output,
        },
        status=response_status,
    )


@login_required
@require_POST
def start_deck_poll_hx(request):
    return render(
        request,
        'crawler/_start_deck_poll.html',
        {},
    )


@login_required
@require_POST
def update_stats(request):
    legal_decks = (
        Deck.objects
        .filter(pdh_legal=True)
        .count()
    )

    s = SiteStat(legal_decks=legal_decks)
    s.save()
    
    return HttpResponseClientRefresh()


@login_required
def log_index(request):
    logs = (
        LogEntry.objects
        .filter(follows=None)
    )
    paginator = Paginator(logs, 10, orphans=3)
    page_number = request.GET.get('page')
    logs_page = paginator.get_page(page_number)

    return render(
        request,
        'crawler/log_index.html',
        {
            'logs': logs_page,
        },
    )


@login_required
def log_from(request, start_log):
    # brute force is best force 💪
    # yes this is gross, but "reversing a linked list" in SQL
    # turns out to be a bad idea.
    logs = (
        LogEntry.objects
        .filter(
            Q(id=start_log) |
            Q(follows__id=start_log) |
            Q(follows__follows__id=start_log) |
            Q(follows__follows__follows__id=start_log) |
            Q(follows__follows__follows__follows__id=start_log) |
            Q(follows__follows__follows__follows__follows__id=start_log) |
            Q(follows__follows__follows__follows__follows__follows__id=start_log) |
            Q(follows__follows__follows__follows__follows__follows__follows__id=start_log) |
            Q(follows__follows__follows__follows__follows__follows__follows__follows__id=start_log) |
            Q(follows__follows__follows__follows__follows__follows__follows__follows__follows__id=start_log)
        )
        .order_by('created')
    )

    template = 'crawler/log.html'
    if request.htmx:
        template = 'crawler/log_partial.html'

    return render(
        request,
        template,
        {
            'logs': logs,
        },
    )
