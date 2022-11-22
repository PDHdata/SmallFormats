"""
See https://www.moxfield.com/help/faq#moxfield-api for more on crawling Moxfield.
"""
from ._crawl_base import CrawlCommand
from decklist.models import DataSource
from crawler.crawlers import MoxfieldCrawler, MOXFIELD_API_BASE


class Command(CrawlCommand):
    help = f'Ask Moxfield for PDH decklists'

    CRAWLER_CLASS = MoxfieldCrawler
    API_BASE = MOXFIELD_API_BASE
    INITIAL_PAGE_ROUTE = "decks/search"
    INITIAL_PAGE_PARAMS = {
        'pageNumber': 1,
        'pageSize': 64,
        'sortType': 'updated',
        'sortDirection': 'Descending',
        'fmt': 'pauperEdh',
    }
    DATASOURCE = DataSource.MOXFIELD
    ID_KEY = 'publicId'
    LAST_UPDATE_KEY = 'lastUpdatedAtUtc'
    NAME_KEY = 'name'
    CREATOR_DISPLAY_KEY_1 = 'createdByUser'
    CREATOR_DISPLAY_KEY_2 = 'userName'
    SOURCE_LINK = 'https://www.moxfield.com/decks/{0}'
    DECK_FETCH_LINK = MOXFIELD_API_BASE + "decks/all/{0}"
