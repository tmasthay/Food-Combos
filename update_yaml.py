"""Collapse the scraped ``Final/`` tree into ``data.yaml``.

    python update_yaml.py
"""

import argparse

from foodcombos.cli import use_utf8_stdout
from foodcombos.database import YAML_PATH, flatten, save_yaml
from foodcombos.paths import DATA_ROOT


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--root', default=DATA_ROOT)
    parser.add_argument('--out', default=YAML_PATH)
    return parser.parse_args(argv)


def main(argv=None):
    use_utf8_stdout()
    args = parse_args(argv)
    tree = save_yaml(path=args.out, root=args.root)
    flat = flatten(tree)
    print('Wrote %s: %d groups, %d foods'
          % (args.out, len(flat), sum(len(v) for v in flat.values())))


if __name__ == '__main__':
    main()
