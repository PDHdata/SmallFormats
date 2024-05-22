import httpx
from smallformats import __version__
from decklist.models import DataSource, Deck
from crawler.models import DeckCrawlResult
from django.utils.dateparse import parse_datetime
from django.db import transaction

ARCHIDEKT_API_BASE = "https://archidekt.com/api/"
MOXFIELD_API_BASE = "https://api2.moxfield.com/v2/"
SCRYFALL_API_BASE = "https://api.scryfall.com/"

HEADERS = {
    'User-agent': f'SmallFormats/{__version__}',
}


def format_response_error(response):
    result = f"{response.status_code} accessing {response.request.url}\n\n"
    for hdr, value in response.headers.items():
        result += f".. {hdr}: {value}\n"
    result += f"\n{response.text}"

    return result


class CrawlerExit(Exception):
    def __init__(self, *args, response: httpx.Response = None):
        super().__init__(*args)
        self.response = response


class _BaseCrawler:
    API_BASE = None
    INITIAL_PAGE_ROUTE = None
    INITIAL_PAGE_PARAMS = None
    SOURCE_LINK = None
    DECK_FETCH_LINK = None

    DATASOURCE = None
    ID_KEY = None
    LAST_UPDATE_KEY = None
    NAME_KEY = None
    CREATOR_DISPLAY_KEY_1 = None
    CREATOR_DISPLAY_KEY_2 = None

    def __init__(self, client: httpx.Client, initial_url, stop_after, write):
        self.stop_after = stop_after
        self._client = client
        self._write = write or print
        self.url = initial_url or self._build_initial_url()
        self._keep_going = True
    
    def _build_initial_url(self):
        req = self._client.build_request(
            "GET",
            self.INITIAL_PAGE_ROUTE,
            params=self.INITIAL_PAGE_PARAMS,
        )
        return req.url
    
    def get_next_page(self):
        if not self._keep_going:
            raise CrawlerExit("this crawler cannot proceed")

        response = self._client.get(self.url)

        # check errors
        if response.status_code < 200 or response.status_code >= 300:
            # report error and bail
            self._keep_going = False
            raise CrawlerExit(f"got {response.status_code} from client", response)
        
        else:
            self._process_response(response)

        return self._keep_going

    def _process_response(self, response: httpx.Response):
        raise NotImplementedError
    
    def _process_page(self, results, stop_after):
        self._write(f"Processing next {len(results)} results.")
        
        # get existing decks for this page
        ids = [str(r[self.ID_KEY]) for r in results]
        qs = Deck.objects.filter(
            source=self.DATASOURCE
        ).filter(source_id__in=ids)
        existing_decks = { d.source_id: d for d in qs }

        for deck_data in results:
            deck_updated_at = parse_datetime(deck_data[self.LAST_UPDATE_KEY])
            if stop_after and deck_updated_at < stop_after:
                # break if we've seen everything back to the right time
                return deck_updated_at

            this_id = str(deck_data[self.ID_KEY])
            if this_id in existing_decks.keys():
                deck = existing_decks[this_id]
                deck.commander = None # reset commander in case it changed
            else:
                deck = Deck()
                deck.pdh_legal = False # until proven otherwise!
            deck.name = deck_data[self.NAME_KEY]
            deck.source = self.DATASOURCE
            deck.source_id = this_id
            deck.source_link = self.SOURCE_LINK.format(this_id)
            # so far, both Archidekt and Moxfield have a fixed 2-level hierarchy
            deck.creator_display_name = deck_data[self.CREATOR_DISPLAY_KEY_1][self.CREATOR_DISPLAY_KEY_2]
            deck.updated_time = deck_updated_at

            crawl_result = DeckCrawlResult(
                url=self.DECK_FETCH_LINK.format(this_id),
                deck=deck,
                updated_time=deck_updated_at,
                got_cards=False,
            )
            with transaction.atomic():
                deck.save()
                crawl_result.save()
        
        # the last deck we processed will have the oldest date
        return deck_updated_at


class ArchidektCrawler(_BaseCrawler):
    API_BASE = ARCHIDEKT_API_BASE
    INITIAL_PAGE_ROUTE = "decks/cards/"
    INITIAL_PAGE_PARAMS = {
        'formats': 17,
        'orderBy': '-updatedAt',
        'size': 100,
        'pageSize': 48,
    }
    SOURCE_LINK = 'https://archidekt.com/decks/{0}'
    DECK_FETCH_LINK = ARCHIDEKT_API_BASE + "decks/{0}/"

    DATASOURCE = DataSource.ARCHIDEKT
    ID_KEY = 'id'
    LAST_UPDATE_KEY = 'updatedAt'
    NAME_KEY = 'name'
    CREATOR_DISPLAY_KEY_1 = 'owner'
    CREATOR_DISPLAY_KEY_2 = 'username'

    def _process_response(self, response):
        envelope = response.json()
        count, next = envelope['count'], envelope['next']

        # Archidekt seems to send "count = -1" under some conditions
        if count <= 0:
            self._keep_going = False
            raise CrawlerExit(f"Archidekt client got: {response.text}", response)

        if next:
            # Archidekt "next" comes back as http:// so fix that up
            if next[0:5] == 'http:':
                next = 'https:' + next[5:]
            self.url = next
        else:
            # reached the end!
            self.url = None
            self._keep_going = False

        oldest_seen = self._process_page(envelope['results'], self.stop_after)
        if self.stop_after and oldest_seen < self.stop_after:
            # we're done!
            self._keep_going = False


class MoxfieldCrawler(_BaseCrawler):
    API_BASE = MOXFIELD_API_BASE
    INITIAL_PAGE_ROUTE = "decks/search"
    INITIAL_PAGE_PARAMS = {
        'pageNumber': 1,
        'pageSize': 64,
        'sortType': 'updated',
        'sortDirection': 'Descending',
        'fmt': 'pauperEdh',
    }
    SOURCE_LINK = 'https://www.moxfield.com/decks/{0}'
    DECK_FETCH_LINK = MOXFIELD_API_BASE + "decks/all/{0}"

    DATASOURCE = DataSource.MOXFIELD
    ID_KEY = 'publicId'
    LAST_UPDATE_KEY = 'lastUpdatedAtUtc'
    NAME_KEY = 'name'
    CREATOR_DISPLAY_KEY_1 = 'createdByUser'
    CREATOR_DISPLAY_KEY_2 = 'userName'

    def _process_response(self, response):
        envelope = response.json()
        count = envelope['totalResults']
        page = envelope['pageNumber']
        totalPages = envelope['totalPages']
        if page < totalPages:
            self.url = response.url.copy_set_param('pageNumber', page + 1)
        else:
            # reached the end!
            self._keep_going = False
            self.url = None

        if count <= 0:
            self._keep_going = False
            raise CrawlerExit(f"Moxfield client got: {response.text}", response)

        oldest_seen = self._process_page(envelope['data'], self.stop_after)
        if self.stop_after and oldest_seen < self.stop_after:
            # we're done!
            self._keep_going = False
