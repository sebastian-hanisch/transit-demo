"""Vorgerechnete Messreihe zum Exakt-Tab (data/exact_results.json, erzeugt von tools/sweep_exact.py): Laden und Textbausteine."""

import json
import os
import pathlib
from functools import lru_cache

PATH = pathlib.Path(os.environ.get("TRANSIT_EXACT_RESULTS_PATH") or pathlib.Path(__file__).parent / "data" / "exact_results.json")


@lru_cache(maxsize=1)
def load():
    with open(PATH, encoding="utf-8") as fh:
        return json.load(fh)


def configs():
    return load()["konfigurationen"]


def stat_text(s, digits=1):
    """„Mittel ± Standardfehler“ mit Dezimalkomma."""
    return f"{s['mean']:.{digits}f} ± {s['se']:.{digits}f}".replace(".", ",")


def share_text(p):
    return f"{p['k']} von {p['n']}"
