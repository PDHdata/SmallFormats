from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django_htmx.http import HttpResponseClientRefresh
from crawler.models import DeckCrawlResult, CrawlRun


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


def new_run(request):
    raise NotImplementedError()


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
