"""
See https://www.moxfield.com/help/faq#moxfield-api for more on crawling Moxfield.
Also note that since November 2024, Moxfield requires an API key.
"""
import os

from ._crawl_base import CrawlCommand
from decklist.models import DataSource
from crawler.crawlers import MoxfieldCrawler, MOXFIELD_API_BASE, HEADERS


MOXFIELD_API_KEY = os.environ.get('SMALLFORMATS_MOXFIELD_USERAGENT')
if not MOXFIELD_API_KEY:
    # TODO: could warn instead of raise
    raise ValueError("Could not get SMALLFORMATS_MOXFIELD_USERAGENT env var")
else:
    _HEADERS = HEADERS.copy()
    _HEADERS.update({
        'User-agent': MOXFIELD_API_KEY,
    })

class Command(CrawlCommand):
    help = f'Ask Moxfield for PDH decklists'

    Crawler = MoxfieldCrawler
    DATASOURCE = DataSource.MOXFIELD
    API_BASE = MOXFIELD_API_BASE
    HEADERS = _HEADERS
