import httpx


class CrawlerExit(Exception):
    def __init__(self, *args, response: httpx.Response = None):
        super().__init__(*args)
        self.response = response


class ArchidektCrawler:
    def __init__(self, initial_url, stop_after, processor):
        self.stop_after = stop_after
        self.url = initial_url
        self.processor = processor
        self._keep_going = True
    
    def get_next_page(self, client: httpx.Client):
        if not self._keep_going:
            raise CrawlerExit("this crawler cannot proceed")

        response = client.get(self.url)

        # check errors
        if response.status_code < 200 or response.status_code >= 300:
            # report error and bail
            self._keep_going = False
            raise CrawlerExit(f"got {response.status_code} from client", response)
        
        else:
            self._process_response(response)

        return self._keep_going

    def _process_response(self, response: httpx.Response):
        envelope = response.json()
        count, next = envelope['count'], envelope['next']

        # Archidekt seems to send "count = -1" under some conditions
        if count <= 0:
            self._keep_going = False
            raise CrawlerExit(f"client got: {response.text}", response)

        if next:
            # Archidekt "next" comes back as http:// so fix that up
            if next[0:5] == 'http:':
                next = 'https:' + next[5:]
            self.url = next
        else:
            # reached the end!
            self.url = None
            self._keep_going = False

        oldest_seen = self.processor(envelope['results'], self.stop_after)
        if self.stop_after and oldest_seen < self.stop_after:
            # we're done!
            self._keep_going = False
