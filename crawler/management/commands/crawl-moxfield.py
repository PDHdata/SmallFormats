"""
See https://www.moxfield.com/help/faq#moxfield-api for more on crawling Moxfield.
"""
from ._crawl_base import CrawlCommand
from decklist.models import DataSource
from crawler.crawlers import MoxfieldCrawler, MOXFIELD_API_BASE


class Command(CrawlCommand):
    help = f'Ask Moxfield for PDH decklists'

    Crawler = MoxfieldCrawler
    DATASOURCE = DataSource.MOXFIELD
    API_BASE = MOXFIELD_API_BASE
