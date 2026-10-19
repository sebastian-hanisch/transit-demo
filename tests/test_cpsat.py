"""CP-SAT-Modell (transit_cpsat) gegen die Aufzählung (transit_exact) als unabhängiges Orakel: Jede Modellverbesserung muss denselben Optimalwert liefern."""

import dataclasses
import random

import pytest

import transit_cpsat as C
import transit_exact as X
from transit_demand import generate_stops_and_demand
from transit_evaluation import evaluate_network
from transit_heuristics import demand_greedy_construction

pytest.importorskip("ortools")

BASE = C.ModelOptions(exact_size=False, lex_symmetry=False, compact_reach=False, hint=False, two_stage=False, line_cuts=False)
FULL = C.ModelOptions()
VARIANTS = {"alles": FULL, "Grundmodell": BASE, **{f"ohne {f.name}": dataclasses.replace(FULL, **{f.name: False}) for f in dataclasses.fields(C.ModelOptions)}}


def _instance(n, seed, hub=0.5):
    coords, demand, _ = generate_stops_and_demand(n, seed, hub, 2)
    return coords, demand


def _key(stats):
    """Auswahlregel der App: erst kleinste nicht erreichbare, dann größte direkte Nachfrage."""
    return (round(stats["unreachable_demand"], 6), -round(stats["direct_demand"], 6))


@pytest.mark.parametrize("name", list(VARIANTS))
def test_every_model_variant_finds_the_enumerated_optimum(name):
    rng = random.Random(3)
    for seed in range(1, 9):
        n, k, length = rng.randint(5, 8), rng.randint(2, 3), rng.randint(3, 5)
        coords, demand = _instance(n, seed, hub=rng.choice([0.0, 0.5, 1.0]))
        exact = X.solve_exact(coords, demand, k, length)
        hint = demand_greedy_construction(coords, demand, k, length)
        r = C.solve_cpsat(demand, k, length, time_limit=30, opts=VARIANTS[name], hint_lines=hint)
        assert r.proven and r.status == "OPTIMAL", (name, seed)
        assert _key(r.stats) == _key(exact.stats_lex), (name, seed, n, k, length)


def test_reported_numbers_come_from_the_apps_own_evaluation():
    coords, demand = _instance(8, 4)
    r = C.solve_cpsat(demand, 3, 4, time_limit=30)
    assert r.stats == evaluate_network(r.lines, demand)
    assert r.reach_demand == pytest.approx(r.stats["direct_demand"] + r.stats["one_transfer_demand"]) and r.direct_demand == pytest.approx(r.stats["direct_demand"])
    assert all(len(line) == 4 and len(set(line)) == 4 for line in r.lines) and len(r.lines) == 3


def test_proven_optimum_has_a_zero_gap_and_the_bound_equals_the_value():
    coords, demand = _instance(9, 2)
    r = C.solve_cpsat(demand, 3, 5, time_limit=30)
    assert r.proven and r.gap_pp == pytest.approx(0.0, abs=1e-6)
    assert r.bound_direct_pct == pytest.approx(r.stats["direct_pct"], abs=1e-6)


def test_a_short_time_limit_returns_a_valid_network_with_a_positive_gap():
    """Auf einer Instanz, die in 0,3 s nicht bewiesen wird, kommt eine zulässige Lösung mit einer Schranke zurück, die nie unter dem erreichten Wert liegt."""
    coords, demand = _instance(14, 5)
    hint = demand_greedy_construction(coords, demand, 4, 6)
    r = C.solve_cpsat(demand, 4, 6, time_limit=0.5, hint_lines=hint)
    assert r.status in ("FEASIBLE", "OPTIMAL") and len(r.lines) == 4 and all(len(set(line)) == 6 for line in r.lines)
    assert r.bound_direct_pct >= r.stats["direct_pct"] - 1e-9 and r.gap_pp >= 0.0
    assert r.stats["direct_pct"] >= evaluate_network(hint, demand)["direct_pct"] - 1e-9 or not r.proven      # die Startlösung wird nicht unterboten, wenn sie zulässig ist


def test_cpsat_never_loses_to_a_heuristic_on_a_larger_instance():
    coords, demand = _instance(12, 3)
    greedy = demand_greedy_construction(coords, demand, 3, 5)
    r = C.solve_cpsat(demand, 3, 5, time_limit=20, hint_lines=greedy)
    assert _key(r.stats) <= _key(evaluate_network(greedy, demand))


def test_pad_hint_gives_full_length_distinct_lines_in_decreasing_order():
    coords, demand = _instance(10, 1)
    lines = C._pad_hint([[0, 1], [2, 3, 4, 5, 6, 7, 8]], demand, 3, 5)
    assert len(lines) == 3 and all(len(l) == 5 and len(set(l)) == 5 for l in lines)
    masks = [sum(1 << s for s in l) for l in lines]
    assert masks == sorted(masks, reverse=True)


def test_invalid_stage_is_rejected():
    _, demand = _instance(6, 1)
    with pytest.raises(ValueError):
        C.build_model(demand, 2, 3, FULL, stage="x")


def test_more_lines_than_candidate_sets_is_handled():
    """Bei k größer als die Zahl der Kandidaten-Linien (n = 5, Länge 5: nur eine Menge) darf die Ordnung der Linien nicht streng sein."""
    coords, demand = _instance(5, 2)
    r = C.solve_cpsat(demand, 2, 5, time_limit=20)
    assert r.proven and r.stats["direct_pct"] == pytest.approx(100.0)


TIGHT = [(9, 2, 4, s) for s in range(1, 6)] + [(8, 2, 3, s) for s in range(1, 4)] + [(9, 3, 3, s) for s in range(1, 4)] + [(10, 2, 4, 1)]


@pytest.mark.parametrize("n,k,length,seed", TIGHT)
def test_instances_where_not_everything_can_be_reached_match_the_enumeration(n, k, length, seed):
    """Zu wenige Linienplätze für alle Paare: Das Optimum lässt Nachfrage unerreichbar, die Umstiegslogik und die Rangfolge (erst Erreichbarkeit, dann direkte Nachfrage) bestimmen den Optimalwert."""
    coords, demand = _instance(n, seed)
    exact = X.solve_exact(coords, demand, k, length)
    for opts in (FULL, BASE):
        r = C.solve_cpsat(demand, k, length, time_limit=30, opts=opts)
        assert r.proven and _key(r.stats) == _key(exact.stats_lex)
    assert exact.stats_lex["unreachable_pct"] > 0


def test_the_rule_ranks_reachability_before_direct_demand():
    """Auf mindestens einer dieser Instanzen hat das Optimum der direkten Nachfrage allein mehr unerreichbare Nachfrage: Die Rangfolge der Zielgröße unterscheidet beide."""
    found = 0
    for n, k, length, seed in TIGHT:
        coords, demand = _instance(n, seed)
        e = X.solve_exact(coords, demand, k, length)
        if e.stats_direct["unreachable_demand"] > e.stats_lex["unreachable_demand"] + 1e-9 and e.stats_direct["direct_demand"] > e.stats_lex["direct_demand"] + 1e-9:
            found += 1
    assert found >= 1
