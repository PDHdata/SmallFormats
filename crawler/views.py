from django.shortcuts import render
from django.core.paginator import Paginator
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
