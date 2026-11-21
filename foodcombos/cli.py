"""Shared bits of the command line entry points."""

import sys


def use_utf8_stdout():
    """Keep Wikipedia's accented titles printable on a cp1252 console."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is not None:
            reconfigure(encoding='utf-8', errors='replace')
