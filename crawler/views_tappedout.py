from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseNotFound
from django.urls import reverse
from django.utils import timezone
from bs4 import BeautifulSoup
import json
from datetime import timedelta
import httpx
from crawler.crawlers import HEADERS


TAPPED_OUT_BASE = "https://tappedout.net"
TAPPED_OUT_URL = "/mtg-decks/search/?q=&format=pauper-edh&price_min=&price_max=&o=-date_updated&submit=Filter results"
TAPPED_OUT_MAX_PAGES = 10

def parse_time_string(time_str):
    now = timezone.now()

    match time_str.split():
        case [num, "minute" | "minutes", "ago"]:
            return now - timedelta(minutes=int(num))
        case [num, "hour" | "hours", "ago"]:
            return now - timedelta(hours=int(num))
        case [num, "day" | "days", "ago"]:
            return now - timedelta(days=int(num))
        case [num, "week" | "weeks", "ago"]:
            return now - timedelta(weeks=int(num))
        case [num, "month" | "months", "ago"]:
            # gross, but close enough for this use
            return now - timedelta(days=int(num) * 30)
        case _:
            # TODO: log this, as it would be a new string
            # we haven't accounted for
            return now


@login_required
def tapped_out_page(request, page_number=1):
    # TappedOut seems to cap searches to 10 pages, so we will too
    if page_number < 1 or page_number > TAPPED_OUT_MAX_PAGES:
        return HttpResponseNotFound(
            content=json.dumps({
                'message': f"no page {page_number}",
            }),
            content_type="application/json"
        )
    
    with httpx.Client(
            headers=HEADERS,
            base_url=TAPPED_OUT_BASE) as c:
        params = {
            'p': page_number,
            'page': page_number,
        }
        r = c.get(TAPPED_OUT_URL, params=params)
        if r.status_code == 200:
            page = BeautifulSoup(r.text)
        else:
            return HttpResponse(
                content=json.dumps({
                    'message': f"got error {r.status_code} from upstream",
                    'upstream': {
                        'statusMessage': r.reason_phrase,
                        'url': str(r.url),
                        'content': r.text,
                    },
                }),
                status=r.status_code,
                content_type="application/json",
            )

    payload = []
    for tag in page.select('div.deck-wide-chart'):
        names_div = tag.next_sibling.next_sibling

        deck_a = names_div.a
        name = ''.join(deck_a.contents).strip()
        href = deck_a['href']
        # decks are linked at "/mtg-decks/<name>/"
        #                      01234567890^
        deck_id = href[11:-1]
        
        user_a = names_div.find('a', title=False)
        username = ''.join(part for part in user_a.stripped_strings)

        time_parent_div = names_div.next_sibling.next
        time_div = time_parent_div.div.contents[-2]
        time_h5 = time_div.h5
        updated_sentence = ''.join(s for s in time_h5.stripped_strings)
        # times are "Updated <num> <units> ago."
        #            01234567^
        updated_time_str = updated_sentence[8:-1]
        updated_time = parse_time_string(updated_time_str)

        uri = f"https://tappedout.net/api/collection:deck/{deck_id}/board/"
        
        payload.append({
            'deckName': name,
            'uri': uri,
            'id': deck_id,
            # both Moxfield and Archidekt nest their usernames. for keeping
            # the implementation of the crawler infra simple, this is nested
            # to match.
            'user': {
                'name': username,
            },
            'lastUpdated': str(updated_time),
            'upstream': {
                'lastUpdated': updated_sentence,
                'uri': TAPPED_OUT_BASE + href,
            },
        })
    
    next_url = request.build_absolute_uri(
        reverse('crawler:tappedout_page', kwargs={'page_number': page_number+1})
    ) if page_number < TAPPED_OUT_MAX_PAGES else None

    return HttpResponse(
        json.dumps({
            'data': payload,
            'next': next_url,
        }),
        content_type="application/json",
    )
