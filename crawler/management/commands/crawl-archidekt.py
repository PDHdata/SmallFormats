"""
See https://archidekt.com/forum/thread/3476605/1 for more on crawling Archidekt.
"""
from ._crawl_base import CrawlCommand
from decklist.models import DataSource
from crawler.crawlers import ArchidektCrawler, ARCHIDEKT_API_BASE


class Command(CrawlCommand):
    help = f'Ask Archidekt for PDH decklists'

    Crawler = ArchidektCrawler
    DATASOURCE = DataSource.ARCHIDEKT
    API_BASE = ARCHIDEKT_API_BASE
