"""Build combinations out of the scraped lists."""

import itertools
import os
import random

from .paths import read_text

COLUMN_GAP = 5


def read_list(path, keep_empty=False):
    lines = read_text(path).split('\n')
    return lines if keep_empty else [line for line in lines if line]


def cartesian(lists, separator=','):
    """Every combination, one per line."""
    return '\n'.join(separator.join(items) for items in itertools.product(*lists))


def columns(lists, gap=COLUMN_GAP):
    """The lists printed side by side, padded with ``gap`` spaces."""
    spacer = ' ' * gap
    height = max((len(column) for column in lists), default=0)
    rows = []
    for index in range(height):
        row = ''
        for column in lists:
            if index < len(column):
                row += column[index]
            row += spacer
        rows.append(row)
    return '\n'.join(rows) + ('\n' if rows else '')


def product_text(input_files, keep_empty=False, as_cartesian=False, gap=COLUMN_GAP):
    """Read ``input_files`` and render them as a product or as columns."""
    if not input_files:
        raise ValueError('No input files given')
    lists = [read_list(path, keep_empty=keep_empty) for path in input_files]
    return cartesian(lists) if as_cartesian else columns(lists, gap=gap)


def sample(population, count, seed=None):
    """``count`` picks from ``population`` (with replacement, like before)."""
    rng = random.Random(seed)
    population = list(population)
    if not population:
        return []
    return [rng.choice(population) for _ in range(count)]


def sample_file(path, count, seed=None):
    return sample(read_list(path), count, seed=seed)


def sample_tree(directory, count, seed=None, suffix='.txt'):
    """Sample from every ``*.txt`` beneath ``directory``."""
    everything = []
    for dirpath, _, filenames in os.walk(directory):
        for name in sorted(filenames):
            if name.endswith(suffix):
                everything.extend(read_list(os.path.join(dirpath, name)))
    return sample(everything, count, seed=seed)
