from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django_htmx.http import HttpResponseClientRefresh
from crawler.models import CrawlRun, LogEntry, LogStart
from decklist.models import Deck, SiteStat


def crawler_index(request):
    try:
        stats = SiteStat.objects.latest()
    except SiteStat.DoesNotExist:
        stats = None

    return render(
        request,
        'crawler/index.html',
        {
            'stats': stats,
            'user_logged_in': request.user.is_authenticated,
        },
    )


def run_index(request):
    runs = CrawlRun.objects.order_by('-crawl_start_time')
    paginator = Paginator(runs, 8, orphans=3)
    page_number = request.GET.get('page')
    runs_page = paginator.get_page(page_number)

    return render(
        request,
        'crawler/run_index.html',
        {
            'runs': runs_page,
        },
    )


def run_detail(request, run_id):
    run = get_object_or_404(CrawlRun, pk=run_id)

    return render(
        request,
        'crawler/run_detail.html',
        {
            'run': run,
            'errored': run.state == CrawlRun.State.ERROR,
            'allow_search_infinite': run.state == CrawlRun.State.NOT_STARTED and run.search_back_to,
            'can_cancel': run.state not in (CrawlRun.State.CANCELLED, CrawlRun.State.COMPLETE),
            'user_logged_in': request.user.is_authenticated,
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
def update_stats(request):
    legal_decks = (
        Deck.objects
        .filter(pdh_legal=True)
        .count()
    )

    s = SiteStat(legal_decks=legal_decks)
    s.save()
    
    return HttpResponseClientRefresh()


def log_index(request):
    logs = LogStart.objects.all()
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


def log_errors(request):
    logs = (
        LogEntry.objects
        .filter(is_stderr=True)
        .order_by('-created')
    )

    paginator = Paginator(logs, 10, orphans=3)
    page_number = request.GET.get('page')
    logs_page = paginator.get_page(page_number)

    return render(
        request,
        'crawler/log_errors.html',
        {
            'logs': logs_page,
        },
    )


def log_one_error(request, logstart_id):
    return log_one(request, logstart_id, limit_to_errors=True)


def log_one(request, logstart_id, limit_to_errors=False):
    log_start = get_object_or_404(LogStart, pk=logstart_id)
    logs = (
        LogEntry.objects
        .filter(parent=log_start)
        .order_by('created')
    )
    if limit_to_errors:
        logs = logs.filter(is_stderr=True)

    paginator = Paginator(logs, 40, orphans=3)
    page_number = request.GET.get('page')
    logs_page = paginator.get_page(page_number)

    return render(
        request,
        'crawler/log.html',
        {
            'log_start': log_start,
            'logs': logs_page,
            'limited_to_errors': limit_to_errors,
        },
    )
