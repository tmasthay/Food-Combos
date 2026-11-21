"""Backwards-compatible shims.

The old tkinter GUI (``gui.py``) imports these names.  The real
implementations now live in :mod:`foodcombos.combos`.
"""

import sys

from foodcombos.combos import sample_file, sample_tree


def get_arg(field, deflt, eval_func, deflt_eval=True):
    """Legacy ``key=value`` command line reader.

    New code should use :mod:`argparse`; this remains only so that old
    scripts and the tkinter GUI keep working.
    """
    parts = ' '.join(sys.argv).split('%s=' % field)
    if len(parts) == 1:
        return eval_func(deflt) if deflt_eval else deflt
    value = parts[1].split(' ')[0] if deflt_eval else parts[1]
    return eval_func(value)


def get_random_combos(combo_file, num_combos):
    return sample_file(combo_file, num_combos)


def get_full_random_combos(directory, num_combos):
    return sample_tree(directory, num_combos)
