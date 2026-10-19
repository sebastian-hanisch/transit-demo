"""Exaktes Optimum (transit_exact) gegen eine unabhängige Vollaufzählung mit der Bewertungsfunktion der App und gegen beide Heuristiken."""

import itertools
import math
import random

import numpy as np
import pytest

import transit_exact as X
from transit_demand import generate_stops_and_demand
from transit_evaluation import evaluate_network
from transit_heuristics import demand_greedy_construction, star_network_construction


def _instance(n, seed, hub=0.5):
    coords, demand, _ = generate_stops_and_demand(n, seed, hub, 2)
    return coords, demand


def _lex_key(stats):
    """Auswahlregel der App: erst kleinste nicht erreichbare, dann größte direkte Nachfrage."""
    return (round(stats["unreachable_demand"], 6), -round(stats["direct_demand"], 6))


def _brute_force(demand, k, length):
    """Vollaufzählung über ALLE Haltestellenmengen der Größe 2 bis length (auch nicht maximale), bewertet mit evaluate_network."""
    n = demand.shape[0]
    sets = [list(c) for size in range(2, length + 1) for c in itertools.combinations(range(n), size)]
    best_lex, best_dir = None, None
    for combo in itertools.combinations(range(len(sets)), k):
        stats = evaluate_network([sets[c] for c in combo], demand)
        lex = _lex_key(stats)
        if best_lex is None or lex < best_lex:
            best_lex = lex
        d = (-round(stats["direct_demand"], 6), round(stats["unreachable_demand"], 6))
        if best_dir is None or d < best_dir:
            best_dir = d
    return best_lex, best_dir


@pytest.mark.parametrize("n,k,length,seed", [(5, 2, 3, 1), (5, 2, 4, 2), (6, 2, 3, 3), (6, 2, 4, 4), (5, 3, 3, 5), (6, 2, 5, 6)])
def test_exact_optimum_equals_the_brute_force_over_all_line_sets(n, k, length, seed):
    """Die Beschränkung auf Linien mit genau min(Länge, n) Haltestellen verliert kein Optimum (Auffüllen verschlechtert nichts)."""
    coords, demand = _instance(n, seed)
    result = X.solve_exact(coords, demand, k, length)
    best_lex, best_dir = _brute_force(demand, k, length)
    assert _lex_key(result.stats_lex) == best_lex
    assert (-round(result.stats_direct["direct_demand"], 6), round(result.stats_direct["unreachable_demand"], 6)) == best_dir


@pytest.mark.parametrize("seed", range(1, 13))
def test_exact_is_never_beaten_by_a_heuristic(seed):
    rng = random.Random(seed)
    n, k, length = rng.randint(6, 9), rng.randint(2, 3), rng.randint(3, 5)
    coords, demand = _instance(n, seed, hub=rng.choice([0.0, 0.5, 1.0]))
    result = X.solve_exact(coords, demand, k, length)
    for lines in (star_network_construction(coords, demand, k, length), demand_greedy_construction(coords, demand, k, length)):
        stats = evaluate_network(lines, demand)
        assert _lex_key(result.stats_lex) <= _lex_key(stats)
        assert result.stats_direct["direct_demand"] >= stats["direct_demand"] - 1e-9


def test_internal_score_matches_evaluate_network_on_random_masks():
    rng = random.Random(7)
    for _ in range(25):
        n = rng.randint(4, 9)
        _, demand = _instance(n, rng.randint(1, 99))
        pi, pj = np.triu_indices(n, 1)
        pw = demand[pi, pj]
        k = rng.randint(1, 4)
        lines = [rng.sample(range(n), rng.randint(2, n)) for _ in range(k)]
        masks = np.array([[sum(1 << s for s in line) for line in lines]], dtype=np.int64)
        direct, reach = X._score(masks, n, pi, pj, pw)
        stats = evaluate_network(lines, demand)
        assert direct[0] == pytest.approx(stats["direct_demand"]) and reach[0] == pytest.approx(stats["direct_demand"] + stats["one_transfer_demand"])


def test_reported_statistics_come_from_the_apps_own_evaluation():
    coords, demand = _instance(8, 3)
    r = X.solve_exact(coords, demand, 3, 4)
    assert r.stats_lex == evaluate_network(r.lines_lex, demand) and r.stats_direct == evaluate_network(r.lines_direct, demand)
    assert all(len(line) == 4 and len(set(line)) == 4 for line in r.lines_lex) and len(r.lines_lex) == 3


def test_combination_counts():
    assert X.n_candidates(10, 5) == 252 and X.n_combinations(10, 3, 5) == math.comb(252, 3) == 2_635_500
    assert X.n_candidates(6, 9) == 1                      # Länge über n: eine einzige Kandidaten-Linie (alle Haltestellen)
    assert X.n_combinations(6, 3, 9) == 1                 # höchstens so viele Linien wie Kandidaten
    coords, demand = _instance(8, 1)
    assert X.solve_exact(coords, demand, 3, 5).n_combinations == X.n_combinations(8, 3, 5)


def test_more_lines_than_candidates_leaves_the_rest_empty():
    coords, demand = _instance(6, 2)
    r = X.solve_exact(coords, demand, 3, 6)
    assert r.lines_lex[0] and r.lines_lex[1:] == [[], []] and r.stats_lex["direct_pct"] == pytest.approx(100.0)


def test_too_large_instances_are_refused_and_bad_input_is_rejected():
    coords, demand = _instance(12, 1)
    with pytest.raises(ValueError, match="zu viele"):
        X.solve_exact(coords, demand, 4, 6)
    with pytest.raises(ValueError):
        X.solve_exact(coords[:1], demand[:1, :1], 2, 3)
    with pytest.raises(ValueError):
        X.solve_exact(coords, demand, 0, 3)


def test_order_line_is_a_permutation_starting_at_the_leftmost_stop():
    coords, _ = _instance(9, 4)
    stops = [1, 3, 4, 6, 8]
    path = X.order_line(coords, stops)
    assert sorted(path) == stops and path[0] == min(stops, key=lambda s: (coords[s][0], s))
    assert X.order_line(coords, [5]) == [5]


def test_the_optimum_is_deterministic():
    coords, demand = _instance(9, 8)
    a, b = X.solve_exact(coords, demand, 3, 4), X.solve_exact(coords, demand, 3, 4)
    assert a.lines_lex == b.lines_lex and a.lines_direct == b.lines_direct


def test_order_line_follows_the_nearest_neighbour_along_a_row_of_stops():
    """Handrechnung: Vier Haltestellen auf einer Geraden werden von links nach rechts verbunden (kein Zickzack)."""
    coords = np.array([[30.0, 5.0], [0.0, 5.0], [10.0, 5.0], [20.0, 5.0]])
    assert X.order_line(coords, [0, 1, 2, 3]) == [1, 2, 3, 0]
