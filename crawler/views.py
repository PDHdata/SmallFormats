from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.urls import reverse
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django_htmx.http import HttpResponseClientRefresh, HttpResponseClientRedirect, HTMX_STOP_POLLING
from crawler.models import DeckCrawlResult, CrawlRun, DataSource
from decklist.models import Deck
import httpx
from crawler.management.commands._api_helpers import HEADERS, ARCHIDEKT_API_BASE, format_response_error
from crawler.crawlers import ArchidektCrawler, CrawlerExit


def crawler_index(request):
    runs = CrawlRun.objects.order_by('-crawl_start_time')
    paginator = Paginator(runs, 25, orphans=3)
    page_number = request.GET.get('page')
    runs_page = paginator.get_page(page_number)

    return render(
        request,
        'crawler/index.html',
        {
            'runs': runs_page,
        },
    )


@require_POST
def new_archidekt_run_hx(request):
    try:
        latest_deck_update = (
            Deck.objects
            .filter(
                source=DataSource.ARCHIDEKT,
                updated_time__isnull=False,
            )
            .latest('updated_time')
        ).updated_time
    except Deck.DoesNotExist:
        latest_deck_update = None

    run = CrawlRun(
        state=CrawlRun.State.NOT_STARTED,
        target=DataSource.ARCHIDEKT,
        crawl_start_time=timezone.now(),
        search_back_to=latest_deck_update,
    )

    run.save()
    return HttpResponseClientRedirect(reverse('crawler:run-detail', args=(run.id,)))


def run_detail(request, run_id):
    run = get_object_or_404(CrawlRun, pk=run_id)

    return render(
        request,
        'crawler/run_detail.html',
        {
            'run': run,
            'resumable': run.state in (CrawlRun.State.NOT_STARTED, CrawlRun.State.FETCHING_DECKS),
            'errored': run.state == CrawlRun.State.ERROR,
        },
    )


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


def _build_initial_url(client):
    params = {
        'formats': 17,
        'orderBy': '-createdAt',
        'size': 100,
        'pageSize': 48,
    }
    req = client.build_request(
        "GET",
        "decks/cards/",
        params=params
    )
    return req.url


def _archidekt_page_processor(results, output: list[str]):
    output.append(f"Processing next {len(results)} results.")
    
    # get existing decks for this page
    ids = [str(r['id']) for r in results]
    qs = Deck.objects.filter(
        source=DataSource.ARCHIDEKT
    ).filter(source_id__in=ids)
    existing_decks = { d.source_id: d for d in qs }

    for deck_data in results:
        this_id = str(deck_data['id'])
        if this_id in existing_decks.keys():
            deck = existing_decks[this_id]
        else:
            deck = Deck()
        deck.name = deck_data['name']
        deck.source = DataSource.ARCHIDEKT
        deck.source_id = this_id
        deck.source_link = f"https://archidekt.com/decks/{this_id}"
        deck.creator_display_name = deck_data['owner']['username']
        deck.updated_time = deck_data['updatedAt']

        crawl_result = DeckCrawlResult(
            url=ARCHIDEKT_API_BASE + f"decks/{this_id}/",
            deck=deck,
            target=DataSource.ARCHIDEKT,
            updated_time=deck_data['updatedAt'],
            got_cards=False,
        )
        with transaction.atomic():
            deck.save()
            crawl_result.save()
    
    # the last deck on the page will have the oldest date
    return parse_datetime(deck.updated_time)


@require_POST
def run_archidekt_onepage_hx(request, run_id):
    run = get_object_or_404(CrawlRun, pk=run_id)

    output = []

    with httpx.Client(
        headers=HEADERS,
        base_url=ARCHIDEKT_API_BASE,
    ) as client:

        if run.state == run.State.NOT_STARTED or not run.next_fetch:
            run.state = run.State.FETCHING_DECKS
            run.next_fetch = _build_initial_url(client)
            run.save()

        processor = lambda results: _archidekt_page_processor(results, output)
        crawler = ArchidektCrawler(run.next_fetch, run.search_back_to, processor)

        response_status = 200

        try:
            if crawler.get_next_page(client):
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


def start_archidekt_poll_hx(request, run_id):
    return render(
        request,
        'crawler/_start_archidekt_poll.html',
        {
            'run_id': run_id,
        },
    )
