"""End-to-end scrape: portal -> directory tree -> pages -> results.txt."""

from .fetch import FetchError, fetch_markdown
from .lists import MIN_RESULTS, process_page
from .paths import DATA_ROOT, exists, iter_dirs, iter_list_dirs, write_text
from .portal import scrape_portal
from .wiki import page_url


def _page_files(page_dir):
    title = page_dir.rsplit('/', 1)[-1]
    return (
        '%s/WebContentsRaw_%s.txt' % (page_dir, title),
        '%s/WebContentClean_%s.txt' % (page_dir, title),
    )


def fetch_pages(root=DATA_ROOT, verbose=True):
    """Fetch every page named by a directory in the tree.

    Already-fetched pages are skipped, so an interrupted run resumes
    where it left off.  Returns ``(fetched, skipped, failed)``.
    """
    directories = iter_dirs(root)
    total = len(directories)
    fetched = skipped = 0
    failures = []
    for index, page_dir in enumerate(directories, start=1):
        title = page_dir.rsplit('/', 1)[-1]
        raw_file, clean_file = _page_files(page_dir)
        if exists(clean_file):
            skipped += 1
            continue
        try:
            raw, markdown = fetch_markdown(page_url(title))
        except FetchError as err:
            failures.append(title)
            print('Failed %d of %d: %s' % (index, total, err))
            continue
        write_text(raw_file, raw)
        write_text(clean_file, markdown)
        fetched += 1
        if verbose:
            print('Fetched %d of %d: %s' % (index, total, title))
    print(
        'Fetched %d, skipped %d, failed %d (of %d directories)'
        % (fetched, skipped, len(failures), total)
    )
    return fetched, skipped, failures


def process_pages(root=DATA_ROOT, min_results=MIN_RESULTS, verbose=True):
    """Extract foods from every ``List_*`` page; return ``{page_dir: foods}``."""
    results = {}
    for page_dir in iter_list_dirs(root):
        foods = process_page(page_dir, min_results=min_results)
        if foods is None:
            print('Unreadable, skipping: %s' % page_dir)
            continue
        results[page_dir] = foods
        if verbose:
            print('%s: %d' % (page_dir, len(foods)))
    kept = sum(1 for v in results.values() if len(v) >= min_results)
    print('%d list pages parsed, %d kept (>= %d foods)'
          % (len(results), kept, min_results))
    return results


def run(refetch=False, root=DATA_ROOT, min_results=MIN_RESULTS, verbose=True):
    """Build the database.  ``refetch`` re-walks the portal and the pages."""
    if refetch:
        scrape_portal(root=root)
        fetch_pages(root=root, verbose=verbose)
    return process_pages(root=root, min_results=min_results, verbose=verbose)
