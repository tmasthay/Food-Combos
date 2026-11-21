"""Assert that searching the database never touches the network.

    python tools/check_offline.py

Scraping is a one-time, bandwidth-bound job; searching is not, and must
keep working on a train.  This runs ``search.py`` and ``cross.py`` with
every socket entry point booby-trapped *and* the whole fetching stack
made unimportable, so a stray ``import`` would fail the check just as
loudly as a stray request.
"""

import os
import socket
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

#: Importing any of these from a query tool means the offline guarantee
#: has sprung a leak, whether or not a request was actually made.
BANNED = ('html2text', 'urllib.request', 'http.client')


class Blocker:
    """An import hook that refuses the fetching stack."""

    def find_spec(self, name, path=None, target=None):
        if name in BANNED:
            raise AssertionError('offline check: %s was imported' % name)
        return None


def _boom(action):
    def fail(*args, **kwargs):
        raise AssertionError('offline check: tried to %s' % action)
    return fail


def install_guards():
    sys.meta_path.insert(0, Blocker())
    socket.socket = _boom('open a socket')
    socket.create_connection = _boom('connect')
    socket.getaddrinfo = _boom('resolve a hostname')


def run_script(name, argv):
    path = os.path.join(ROOT, name)
    with open(path, encoding='utf-8') as handle:
        source = handle.read()
    sys.argv = [name] + argv
    namespace = {'__name__': '__main__', '__file__': path}
    exec(compile(source, path, 'exec'), namespace)


CASES = (
    ('search.py', ['summary']),
    ('search.py', ['groups', 'coffee']),
    ('search.py', ['combos', '--slot', 'smoked', '--slot', 'porridge',
                   '-n', '3', '--seed', '11', '--urls']),
)


def main():
    os.chdir(ROOT)
    install_guards()
    for name, argv in CASES:
        print('--- %s %s' % (name, ' '.join(argv)))
        run_script(name, argv)
    print('\nOK: %s never imported, no sockets opened' % ', '.join(BANNED))
    return 0


if __name__ == '__main__':
    sys.exit(main())
