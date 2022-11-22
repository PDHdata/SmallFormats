"""
See https://archidekt.com/forum/thread/3476605/1 for more on crawling Archidekt.
"""
from ._crawl_base import CrawlCommand
from decklist.models import DataSource
from crawler.crawlers import ArchidektCrawler, ARCHIDEKT_API_BASE


class Command(CrawlCommand):
    help = f'Ask Archidekt for PDH decklists'

    CRAWLER_CLASS = ArchidektCrawler
    API_BASE = ARCHIDEKT_API_BASE
    INITIAL_PAGE_ROUTE = "decks/cards/"
    INITIAL_PAGE_PARAMS = {
        'formats': 17,
        'orderBy': '-createdAt',
        'size': 100,
        'pageSize': 48,
    }
    DATASOURCE = DataSource.ARCHIDEKT
    ID_KEY = 'id'
    LAST_UPDATE_KEY = 'updatedAt'
    NAME_KEY = 'name'
    CREATOR_DISPLAY_KEY_1 = 'owner'
    CREATOR_DISPLAY_KEY_2 = 'username'
    SOURCE_LINK = 'https://archidekt.com/decks/{0}'
    DECK_FETCH_LINK = ARCHIDEKT_API_BASE + "decks/{0}/"
