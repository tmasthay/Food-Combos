"""Load the scraped ``Final/`` tree into plain Python containers.

Two views of the same data:

``load_tree``  nested dicts mirroring the directories, lists at the leaves
``load_flat``  ``{'Meals.Sweets.List_of_cakes': ['Angel_cake', ...]}``

``data.yaml`` is just ``load_tree`` dumped to disk; the GUI reads it.
"""

import os

import yaml

from .paths import DATA_ROOT, RESULTS_NAME, read_text

YAML_PATH = 'data.yaml'


def _foods(path):
    lines = (line.strip() for line in read_text(path).splitlines())
    return [line for line in lines if line]


def load_flat(root=DATA_ROOT):
    """Return ``{dotted_group_name: [food, ...]}`` for every results file."""
    groups = {}
    for dirpath, _, filenames in os.walk(root):
        if RESULTS_NAME not in filenames:
            continue
        relative = os.path.relpath(dirpath, root).replace('\\', '/')
        key = relative.replace('/', '.')
        groups[key] = _foods(os.path.join(dirpath, RESULTS_NAME))
    return dict(sorted(groups.items()))


def nest(flat):
    """Expand dotted keys into nested dicts."""
    tree = {}
    for key, foods in flat.items():
        node = tree
        parts = key.split('.')
        for part in parts[:-1]:
            child = node.setdefault(part, {})
            if not isinstance(child, dict):
                # A page title that is also a prefix of another path;
                # keep the deeper structure and move the list aside.
                child = node[part] = {'_items': child}
            node = child
        node[parts[-1]] = foods
    return tree


def load_tree(root=DATA_ROOT):
    return nest(load_flat(root=root))


def save_yaml(path=YAML_PATH, root=DATA_ROOT):
    tree = load_tree(root=root)
    with open(path, 'w', encoding='utf-8') as handle:
        yaml.dump(tree, handle, allow_unicode=True)
    return tree


def load_yaml(path=YAML_PATH):
    with open(path, 'r', encoding='utf-8') as handle:
        return yaml.safe_load(handle)


def flatten(tree, prefix=''):
    """Inverse of :func:`nest`."""
    flat = {}
    for key, value in tree.items():
        dotted = '%s.%s' % (prefix, key) if prefix else key
        if isinstance(value, dict):
            flat.update(flatten(value, dotted))
        else:
            flat[dotted] = value
    return flat
