"""Messreihe zum Exakt-Tab (data/exact_results.json): innere Konsistenz, Nachrechnung einer Instanz und jede README-Zahl."""

from pathlib import Path

import pytest

import transit_exact as X
import transit_exact_results as R
from transit_demand import generate_stops_and_demand
from transit_evaluation import evaluate_network
from transit_heuristics import demand_greedy_construction, star_network_construction

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
CFG = {(c["n"], c["k"], c["L"]): c for c in R.configs()}
st = R.stat_text


def de_int(x):
    return f"{x:,}".replace(",", ".").replace(".", "\u202f") if False else f"{x:,}".replace(",", " ")


def test_structure_and_counts():
    assert set(CFG) == {(8, 3, 5), (9, 2, 4), (10, 3, 5)}
    for (n, k, length), c in CFG.items():
        assert c["combos"] == X.n_combinations(n, k, length)
        assert c["greedy"]["direct"]["n"] == c["star"]["direct"]["n"] == 100


def test_no_heuristic_beats_the_optimum_and_the_gap_is_not_negative():
    for c in CFG.values():
        for m in ("star", "greedy"):
            assert c[m]["nie_besser_als_optimum"] == {"k": 100, "n": 100, "p": 1.0}
            assert c[m]["luecke_direkt_zur_oberen_schranke"]["mean"] >= 0
            assert c[m]["direct"]["mean"] <= c["exakt"]["direct_obere_schranke"]["mean"]


def test_the_demand_driven_heuristic_is_closer_to_the_optimum_than_the_star():
    for c in CFG.values():
        assert c["greedy"]["luecke_direkt_zur_oberen_schranke"]["mean"] < c["star"]["luecke_direkt_zur_oberen_schranke"]["mean"]
        assert c["greedy_besser_als_star_direkt"]["p"] >= 0.9


@pytest.mark.parametrize("cfg,seed", [((8, 3, 5), 1), ((8, 3, 5), 42), ((9, 2, 4), 7), ((10, 3, 5), 3)])
def test_one_instance_of_the_series_is_reproduced(cfg, seed):
    """Dieselbe Instanz neu gerechnet: die Messreihe stützt sich auf genau diese Funktionen (Seed, Pendler-Konzentration 0,5, zwei Hubs)."""
    n, k, length = cfg
    coords, demand, _ = generate_stops_and_demand(n, seed, 0.5, 2)
    ex = X.solve_exact(coords, demand, k, length)
    greedy = evaluate_network(demand_greedy_construction(coords, demand, k, length), demand)
    star = evaluate_network(star_network_construction(coords, demand, k, length), demand)
    assert ex.stats_direct["direct_pct"] >= greedy["direct_pct"] - 1e-9 and ex.stats_direct["direct_pct"] >= star["direct_pct"] - 1e-9
    assert ex.n_combinations == CFG[cfg]["combos"]


def has(text):
    assert text in README, text


def test_the_readme_table_and_statements():
    for key, label in (((8, 3, 5), "8, 3, 5 (27 720 Netze)"), ((9, 2, 4), "9, 2, 4 (7 875 Netze)"), ((10, 3, 5), "10, 3, 5 (2 635 500 Netze")):
        c = CFG[key]
        assert de_int(c["combos"]) in label
        has(label)
        has(f"| {st(c['exakt']['direct_obere_schranke'])} % |")
        has(f"{st(c['star']['direct'])} % (Abstand {st(c['star']['luecke_direkt_zur_oberen_schranke'])} Punkte)")
        has(f"{st(c['greedy']['direct'])} % (Abstand {st(c['greedy']['luecke_direkt_zur_oberen_schranke'])} Punkte)")
    has(f"{st(CFG[(10, 3, 5)]['solve_seconds'], 2)} s je Instanz")
    gaps_g = [c["greedy"]["luecke_direkt_zur_oberen_schranke"]["mean"] for c in CFG.values()]
    gaps_s = [c["star"]["luecke_direkt_zur_oberen_schranke"]["mean"] for c in CFG.values()]
    has(f"{min(gaps_g):.1f}".replace(".", ",") + " bis " + f"{max(gaps_g):.1f}".replace(".", ",") + " Prozentpunkte gegenüber " + f"{min(gaps_s):.1f}".replace(".", ",") + " bis " + f"{max(gaps_s):.1f}".replace(".", ",") + " beim Sternnetz")
    order = ((8, 3, 5), (9, 2, 4), (10, 3, 5))
    wins = [CFG[k]["greedy_besser_als_star_direkt"]["k"] for k in order]
    has(f"in {wins[0]}, {wins[1]} und {wins[2]} von 100 Instanzen")
    hits = [CFG[k]["greedy"]["optimum_getroffen"]["k"] for k in order]
    has(f"({hits[0]}, {hits[1]} und {hits[2]} von 100 Instanzen)")
    has(f"{st(CFG[(9, 2, 4)]['exakt']['unreachable'])} % der Nachfrage unerreichbar")
    assert CFG[(9, 2, 4)]["greedy"]["direct"]["mean"] > CFG[(9, 2, 4)]["exakt"]["direct"]["mean"]       # direkte Nachfrage über dem Optimum der Auswahlregel


def test_file_is_small():
    assert (ROOT / "data" / "exact_results.json").stat().st_size < 20_000
