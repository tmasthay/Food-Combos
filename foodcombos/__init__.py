"""Food-Combos: scrape Wikipedia food lists, then mix them into combinations.

The package is deliberately small and dependency-light:

``paths``     filesystem helpers (Windows-safe, utf-8 everywhere)
``wiki``      Wikipedia title -> URL (stdlib only, no network)
``fetch``     polite Wikipedia fetching (User-Agent, retries, on-disk cache)
``portal``    turns ``Portal:Food`` into the ``Final/`` directory tree
``lists``     turns a fetched ``List_of_*`` page into ``results.txt``
``database``  loads the scraped tree into a nested dict / ``data.yaml``
``combos``    products and random samples over the loaded database
``api``       human-guided narrowed search (see ``CLAUDE.md``)
"""

__all__ = [
    'api',
    'combos',
    'database',
    'fetch',
    'lists',
    'paths',
    'portal',
    'wiki',
]
