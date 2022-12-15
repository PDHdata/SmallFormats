"""
TappedOut doesn't have a full, available API. SmallFormats includes a scraper-based
API implementation to find decks.
"""
from ._crawl_base import CrawlCommand
from decklist.models import DataSource
from crawler.crawlers import TappedOutCrawler, TAPPEDOUT_API_BASE


class Command(CrawlCommand):
    help = f'Ask TappedOut for PDH decklists'

    Crawler = TappedOutCrawler
    DATASOURCE = DataSource.TAPPED_OUT
    API_BASE = TAPPEDOUT_API_BASE
