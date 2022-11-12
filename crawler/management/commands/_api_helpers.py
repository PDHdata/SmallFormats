from smallformats import __version__

ARCHIDEKT_API_BASE = "https://archidekt.com/api/"
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
