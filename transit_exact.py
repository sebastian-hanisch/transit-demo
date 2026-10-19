"""
Exaktes Optimum des Liniennetz-Designs auf kleinen Instanzen (vollständige Aufzählung).

Die Bewertung (`evaluate_network`) hängt nur davon ab, welche Haltestellen eine Linie verbindet, nicht von ihrer Reihenfolge: Ein Paar ist direkt
erreichbar, wenn beide Haltestellen auf derselben Linie liegen, mit einem Umstieg, wenn zwei Linien eine gemeinsame Haltestelle haben. Zwei Folgerungen
machen die Aufzählung klein:

1. Eine Linie ist eine Menge von Haltestellen (die Reihenfolge ist nur für die Karte wichtig).
2. Eine zusätzliche Haltestelle auf einer Linie verschlechtert keine Erreichbarkeit. Es genügen deshalb Linien mit genau min(max. Länge, n) Haltestellen:
   Jede Lösung mit kürzeren Linien lässt sich durch Auffüllen nicht verschlechtern.

Alle Kombinationen von k solchen Linien werden vektorisiert mit Bitmasken bewertet. Zielgröße wie in der Primäransicht der App: erst die kleinste
nicht erreichbare Nachfrage, bei Gleichstand die größte direkte Nachfrage (lexikografisch); zusätzlich das Optimum der direkten Nachfrage allein
(obere Schranke für jede Heuristik). Gleichstände entscheidet die Reihenfolge der Aufzählung (kleinste Haltestellen-Indizes zuerst).
"""

import itertools
import math
import time
from dataclasses import dataclass

import numpy as np

from transit_evaluation import evaluate_network

MAX_COMBINATIONS = 3_000_000   # größere Instanzen werden nicht aufgezählt


def n_candidates(n_stops, max_line_length):
    """Zahl der Kandidaten-Linien: Teilmengen mit genau min(Länge, n) Haltestellen."""
    return math.comb(n_stops, min(max_line_length, n_stops))


def n_combinations(n_stops, n_lines, max_line_length):
    """Zahl der Netze, die aufgezählt werden: k verschiedene Kandidaten-Linien ohne Beachtung der Reihenfolge (höchstens so viele Linien wie Kandidaten)."""
    c = n_candidates(n_stops, max_line_length)
    return math.comb(c, min(n_lines, c))


def order_line(coords, stops):
    """Reihenfolge einer Linie für die Karte: Nächster-Nachbar-Weg ab der Haltestelle ganz links (nur Darstellung, die Bewertung ignoriert die Reihenfolge)."""
    remaining = sorted(stops, key=lambda s: (float(coords[s][0]), s))
    path = [remaining.pop(0)]
    while remaining:
        last = coords[path[-1]]
        nxt = min(remaining, key=lambda s: (float(np.linalg.norm(coords[s] - last)), s))
        remaining.remove(nxt)
        path.append(nxt)
    return path


def _combination_chunks(n_items, k, chunk):
    it = itertools.combinations(range(n_items), k)
    while True:
        flat = np.fromiter(itertools.chain.from_iterable(itertools.islice(it, chunk)), dtype=np.int64)
        if flat.size == 0:
            return
        yield flat.reshape(-1, k)


def _score(masks, n, pi, pj, pw):
    """Direkte und erreichbare (höchstens ein Umstieg) Nachfrage für jede Zeile von `masks` (Netze × Linien, je Linie eine Bitmaske der Haltestellen)."""
    shifts = np.arange(n, dtype=np.int64)
    has = ((masks[:, :, None] >> shifts) & 1).astype(bool)                       # Netz, Linie, Haltestelle
    inter = (masks[:, :, None] & masks[:, None, :]) != 0                         # Linien mit gemeinsamer Haltestelle (auch jede mit sich selbst)
    union_touching = np.bitwise_or.reduce(np.where(inter, masks[:, None, :], 0), axis=2)
    direct_mask = np.bitwise_or.reduce(np.where(has, masks[:, :, None], 0), axis=1)          # je Haltestelle: alle Haltestellen auf gemeinsamen Linien
    reach_mask = np.bitwise_or.reduce(np.where(has, union_touching[:, :, None], 0), axis=1)  # ... mit höchstens einem Umstieg
    direct = (((direct_mask[:, pi] >> pj) & 1) * pw).sum(axis=1)
    reach = (((reach_mask[:, pi] >> pj) & 1) * pw).sum(axis=1)
    return direct, reach


@dataclass
class ExactResult:
    lines_lex: list            # Optimum nach der Auswahlregel der App (kleinste nicht erreichbare, dann größte direkte Nachfrage)
    lines_direct: list         # Optimum der direkten Nachfrage allein
    stats_lex: dict            # evaluate_network des Optimums (unabhängig vom Aufzähler gerechnet)
    stats_direct: dict
    n_combinations: int
    n_candidates: int
    seconds: float


def solve_exact(coords, demand, n_lines, max_line_length, chunk=150_000):
    """Vollständige Aufzählung (siehe Modulbeschreibung). Wirft ValueError, wenn mehr als MAX_COMBINATIONS Netze aufzuzählen wären."""
    t0 = time.perf_counter()
    n = demand.shape[0]
    if n < 2 or n_lines < 1 or max_line_length < 2:
        raise ValueError("mindestens 2 Haltestellen, 1 Linie und Linienlänge 2")
    m = min(max_line_length, n)
    cands = [c for c in itertools.combinations(range(n), m)]
    masks_all = np.array([sum(1 << s for s in c) for c in cands], dtype=np.int64)
    k = min(n_lines, len(cands))
    total_combos = math.comb(len(cands), k)
    if total_combos > MAX_COMBINATIONS:
        raise ValueError(f"{total_combos} Netze sind zu viele für die Aufzählung (Grenze {MAX_COMBINATIONS})")

    pi, pj = np.triu_indices(n, 1)
    pw = np.asarray(demand, dtype=float)[pi, pj]
    keep = pw > 0
    pi, pj, pw = pi[keep], pj[keep], pw[keep]
    total = float(pw.sum())
    scale = total + 1.0

    best_lex, best_dir = (math.inf, None), (math.inf, None)
    for idx in _combination_chunks(len(cands), k, chunk):
        masks = masks_all[idx]
        direct, reach = _score(masks, n, pi, pj, pw)
        key_lex = (total - reach) * scale - direct          # kleinste nicht erreichbare, dann größte direkte Nachfrage
        key_dir = -direct * scale + (total - reach)         # größte direkte, dann kleinste nicht erreichbare
        i = int(np.argmin(key_lex))
        if key_lex[i] < best_lex[0]:
            best_lex = (float(key_lex[i]), idx[i].copy())
        j = int(np.argmin(key_dir))
        if key_dir[j] < best_dir[0]:
            best_dir = (float(key_dir[j]), idx[j].copy())

    def to_lines(index_row):
        return [order_line(coords, list(cands[c])) for c in index_row]

    lines_lex, lines_dir = to_lines(best_lex[1]), to_lines(best_dir[1])
    while len(lines_lex) < n_lines:             # mehr Linien verlangt als Kandidaten: der Rest bleibt leer
        lines_lex.append([])
        lines_dir.append([])
    return ExactResult(lines_lex, lines_dir, evaluate_network(lines_lex, demand), evaluate_network(lines_dir, demand), total_combos, len(cands), time.perf_counter() - t0)
