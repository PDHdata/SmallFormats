"""
See https://www.moxfield.com/help/faq#moxfield-api for more on crawling Moxfield.
Also note that since November 2024, Moxfield requires an API key.
"""
from django.conf import settings

from ._crawl_base import CrawlCommand
from decklist.models import DataSource
from crawler.crawlers import MoxfieldCrawler, MOXFIELD_API_BASE, HEADERS


if settings.MOXFIELD_API_KEY:
    _HEADERS = HEADERS.copy()
    _HEADERS.update({
        'User-agent': settings.MOXFIELD_API_KEY,
    })
else:
    # TODO: could warn instead of raise
    raise ValueError("Could not get settings.MOXFIELD_API_KEY; is SMALLFORMATS_MOXFIELD_USERAGENT set in the environment?")

class Command(CrawlCommand):
    help = f'Ask Moxfield for PDH decklists'

    Crawler = MoxfieldCrawler
    DATASOURCE = DataSource.MOXFIELD
    API_BASE = MOXFIELD_API_BASE
    HEADERS = _HEADERS
