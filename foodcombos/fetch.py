"""Polite Wikipedia fetching.

Three things here are load-bearing, and all three were learned the hard
way:

1. Wikimedia answers requests that carry no descriptive ``User-Agent``
   with HTTP 429 and an error *page*.  A scraper that ignores status
   codes happily stores 1000 copies of that error page and reports
   success, which is exactly what happened to the original version of
   this script.
2. Transient 429/5xx responses need a backoff, not a shrug.
3. Consecutive requests need a small delay; Wikimedia's robot policy
   asks for serial, unhurried access.
"""

import time
import urllib.error
import urllib.request

from html2text import html2text

#: Wikimedia's robot policy asks for a contact address in the User-Agent.
USER_AGENT = (
    'Food-Combos/0.2 (https://github.com/tmasthay/Food-Combos; '
    'tylermasthay@gmail.com) python-urllib'
)

#: Seconds to wait between successive requests.
REQUEST_DELAY = 0.25

#: Retry schedule, in seconds, for 429/5xx and network errors.
BACKOFF = (1, 2, 4, 8, 16)

_last_request = [0.0]


class FetchError(RuntimeError):
    """Raised when a page could not be retrieved after every retry."""


def _throttle():
    elapsed = time.monotonic() - _last_request[0]
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)
    _last_request[0] = time.monotonic()


def fetch_html(url, backoff=BACKOFF):
    """GET ``url`` and return its body as text, or raise ``FetchError``.

    Unlike a bare ``curl``, an HTTP error is an error: nothing is ever
    returned to the caller except a genuine 200 body.
    """
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    last = None
    for attempt, pause in enumerate((0,) + tuple(backoff)):
        if pause:
            time.sleep(pause)
        _throttle()
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                charset = response.headers.get_content_charset() or 'utf-8'
                return response.read().decode(charset, errors='replace')
        except urllib.error.HTTPError as err:
            last = err
            if err.code not in (408, 429, 500, 502, 503, 504):
                break
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            last = err
    raise FetchError('%s: %s' % (url, last))


def fetch_markdown(url):
    """Fetch ``url`` and return ``(raw_html, html2text_markdown)``."""
    raw = fetch_html(url)
    return raw, html2text(raw)
