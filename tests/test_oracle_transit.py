"""Unabhaengige Orakel fuer das Liniennetz-Design: networkx-Kuerzeste-Wege im bipartiten
Haltestellen-Linien-Graphen (Laenge 2 = direkt, 4 = ein Umstieg, sonst nicht erreichbar) gegen
evaluate_network, Brute-Force-Optimum der direkten Nachfrage auf winzigen Instanzen als obere
Schranke beider Heuristiken sowie die README-Kennzahlen, mit dem Orakel nachgerechnet."""

import itertools
import random

import numpy as np
import pytest

from transit_demand import generate_stops_and_demand
from transit_evaluation import evaluate_network, stops_with_unreachable_demand
from transit_heuristics import demand_greedy_construction, star_network_construction

nx = pytest.importorskip("networkx")


def _graph_oracle(lines, demand):
    n = demand.shape[0]
    g = nx.Graph()
    g.add_nodes_from(("s", s) for s in range(n))
    for li, line in enumerate(lines):
        g.add_node(("l", li))
        g.add_edges_from((("l", li), ("s", s)) for s in line)
    total = direct = one = unreach = 0.0
    affected = set()
    for i in range(n):
        for j in range(i + 1, n):
            w = demand[i][j]
            if w <= 0:
                continue
            total += w
            try:
                length = nx.shortest_path_length(g, ("s", i), ("s", j))
            except nx.NetworkXNoPath:
                length = None
            if length == 2:
                direct += w
            elif length == 4:
                one += w
            else:
                unreach += w
                affected.update((i, j))
    return total, direct, one, unreach, affected


def test_evaluate_network_matches_graph_oracle_on_random_networks():
    rng = random.Random(1)
    for _ in range(150):
        n, n_lines = rng.randint(1, 12), rng.randint(0, 6)
        lines = [[rng.randrange(n) for _ in range(rng.randint(0, 5))] for _ in range(n_lines)]  # auch Duplikate/leer
        demand = np.triu(np.array([[rng.choice([0, 0, 1, 2, 5, 9]) for _ in range(n)] for _ in range(n)], dtype=float), 1)
        demand = demand + demand.T
        total, direct, one, unreach, affected = _graph_oracle(lines, demand)
        result = evaluate_network(lines, demand)
        assert result["total_demand"] == pytest.approx(total)
        if total > 0:
            assert result["direct_pct"] == pytest.approx(direct / total * 100)
            assert result["one_transfer_pct"] == pytest.approx(one / total * 100)
            assert result["unreachable_pct"] == pytest.approx(unreach / total * 100)
        assert stops_with_unreachable_demand(lines, demand) == affected


def _best_direct_demand(demand, n, n_lines, max_len):
    subsets = [frozenset(c) for r in range(max_len + 1) for c in itertools.combinations(range(n), r)]
    pairs = [(i, j, demand[i][j]) for i in range(n) for j in range(i + 1, n) if demand[i][j] > 0]
    return max(
        sum(w for i, j, w in pairs if any(i in s and j in s for s in combo))
        for combo in itertools.combinations_with_replacement(subsets, n_lines)
    )


def test_heuristics_never_exceed_brute_force_optimum_of_direct_demand():
    rng = random.Random(2)
    gaps = []
    for k in range(40):
        n, n_lines, max_len = rng.randint(4, 5), rng.randint(1, 2), rng.randint(2, 3)
        coords, demand, _hubs = generate_stops_and_demand(n, 1000 + k, hub_concentration=rng.choice([0, 0.5, 1.0]), n_hubs=1)
        optimum = _best_direct_demand(demand, n, n_lines, max_len)
        for heuristic in (star_network_construction, demand_greedy_construction):
            direct = evaluate_network(heuristic(coords, demand, n_lines, max_len), demand)["direct_demand"]
            assert direct <= optimum + 1e-9
            if heuristic is demand_greedy_construction:
                gaps.append(optimum - direct)
    assert sum(g < 1e-9 for g in gaps) >= len(gaps) // 2  # Greedy trifft das Optimum meistens


def test_readme_benchmark_numbers_with_oracle():
    ranges = {"star": (44.9, 48.1), "greedy": (66.6, 68.9)}
    seen = {"star": [], "greedy": []}
    for seed in range(1, 6):
        coords, demand, _hubs = generate_stops_and_demand(20, seed, 0.6, 2)
        for key, heuristic in (("star", star_network_construction), ("greedy", demand_greedy_construction)):
            total, direct, _one, unreach, _aff = _graph_oracle(heuristic(coords, demand, 4, 7), demand)
            assert unreach == 0.0
            seen[key].append(direct / total * 100)
    for key, (lo, hi) in ranges.items():
        assert min(seen[key]) == pytest.approx(lo, abs=0.05) and max(seen[key]) == pytest.approx(hi, abs=0.05)


def test_readme_multiple_centres_example_with_oracle():
    coords, demand, _hubs = generate_stops_and_demand(30, 8, 0.6, 3)
    t, d, _o, u, _a = _graph_oracle(star_network_construction(coords, demand, 6, 7), demand)
    assert (d / t * 100, u) == (pytest.approx(34.5, abs=0.05), 0.0)
    lines = demand_greedy_construction(coords, demand, 6, 7)
    t, d, _o, u, _a = _graph_oracle(lines, demand)
    assert d / t * 100 == pytest.approx(57.5, abs=0.05) and u / t * 100 == pytest.approx(13.0, abs=0.05)
    assert len({s for line in lines for s in line}) == 27
