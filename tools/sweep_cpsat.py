"""Messreihe zum CP-SAT-Modell: (A) Übereinstimmung mit der Aufzählung, (B) Wirkung jeder Modellverbesserung (Ablation), (C) Skalierung bis zur Größe der Hauptansicht.

Aufruf:  python -B tools/sweep_cpsat.py [Zeitlimit in s]      (Standard 30; läuft rund eine Stunde, ein Prozess, damit die Zeiten nicht von parallelen Läufen verzerrt werden)
Ergebnis: data/cpsat_results.json (Statistikfelder {n, mean, se, med, p10, p90}, Anteile {k, n, p}); keine Rohdaten."""
import dataclasses
import json
import math
import os
import platform
import sys
import time

sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402

import transit_cpsat as C  # noqa: E402
import transit_exact as X  # noqa: E402
from transit_demand import generate_stops_and_demand  # noqa: E402
from transit_evaluation import evaluate_network  # noqa: E402
from transit_heuristics import demand_greedy_construction  # noqa: E402

OUT = os.path.join(ROOT, "data", "cpsat_results.json")
HUB, N_HUBS = 0.5, 2
FULL = C.ModelOptions()
BASE = C.ModelOptions(exact_size=False, lex_symmetry=False, compact_reach=False, hint=False, two_stage=False, line_cuts=False)
ABLATION_INSTANCES = [(10, 3, 5, 1), (10, 3, 5, 2), (10, 3, 5, 3), (11, 3, 5, 1), (11, 3, 5, 2), (12, 3, 5, 1), (12, 3, 5, 2), (12, 3, 6, 5)]
SCALING = [(10, 3, 5), (12, 3, 6), (12, 4, 5), (14, 4, 6), (16, 4, 6), (20, 4, 7)]
SCALING_SEEDS = list(range(1, 11))
ABLATION_LABELS = {"Grundmodell": "Grundmodell (alle Verbesserungen aus)", "alles": "alle Verbesserungen", "exact_size": "ohne exact_size", "lex_symmetry": "ohne lex_symmetry",
                   "compact_reach": "ohne compact_reach", "hint": "ohne hint", "two_stage": "ohne two_stage", "line_cuts": "ohne line_cuts"}


def instance(n, seed):
    coords, demand, _ = generate_stops_and_demand(n, seed, HUB, N_HUBS)
    return coords, demand


def stat(xs):
    a = np.asarray(xs, float)
    se = float(a.std(ddof=1) / math.sqrt(len(a))) if len(a) > 1 else 0.0
    return dict(n=int(len(a)), mean=float(a.mean()), se=se, med=float(np.median(a)), p10=float(np.percentile(a, 10)), p90=float(np.percentile(a, 90)))


def share(flags):
    k = int(sum(flags))
    return dict(k=k, n=len(flags), p=k / len(flags))


def rnd(o):
    if isinstance(o, dict):
        return {k: rnd(v) for k, v in o.items()}
    if isinstance(o, list):
        return [rnd(v) for v in o]
    if isinstance(o, float):
        return float("%.6g" % o)
    return o


def key(stats):
    return (round(stats["unreachable_demand"], 6), -round(stats["direct_demand"], 6))


def part_a(limit):
    """Dieselbe Zielgröße wie die Aufzählung auf kleinen Instanzen (n 7 bis 10)."""
    rows = []
    for n in (7, 8, 9, 10):
        for k, length in ((2, 4), (3, 5), (3, 4)):
            for seed in range(1, 6):
                coords, demand = instance(n, seed)
                ex = X.solve_exact(coords, demand, k, length)
                r = C.solve_cpsat(demand, k, length, time_limit=limit, hint_lines=demand_greedy_construction(coords, demand, k, length))
                rows.append(dict(proven=r.proven, equal=key(r.stats) == key(ex.stats_lex), t_cp=r.seconds, t_enum=ex.seconds))
        print("A n =", n, flush=True)
    return dict(instanzen=len(rows), bewiesen=share([r["proven"] for r in rows]), gleiches_optimum=share([r["equal"] for r in rows if r["proven"]]),
                sekunden_cpsat=stat([r["t_cp"] for r in rows]), sekunden_aufzaehlung=stat([r["t_enum"] for r in rows]))


def part_b(limit):
    variants = {"Grundmodell": BASE, "alles": FULL}
    for f in dataclasses.fields(C.ModelOptions):
        variants[f.name] = dataclasses.replace(FULL, **{f.name: False})
    out = {}
    for name, opts in variants.items():
        rows = []
        for n, k, length, seed in ABLATION_INSTANCES:
            coords, demand = instance(n, seed)
            hint = demand_greedy_construction(coords, demand, k, length)
            r = C.solve_cpsat(demand, k, length, time_limit=limit, hint_lines=hint, opts=opts)
            rows.append(dict(proven=r.proven, secs=min(r.seconds, limit), direct=r.stats["direct_pct"], gap=r.gap_pp if r.proven or opts.two_stage else float("nan")))
            print("B", name, n, k, length, seed, "%.1fs" % r.seconds, r.status, flush=True)
        out[name] = dict(label=ABLATION_LABELS[name], bewiesen=share([r["proven"] for r in rows]), sekunden=stat([r["secs"] for r in rows]),
                         summe_sekunden=float(sum(r["secs"] for r in rows)), direkt=stat([r["direct"] for r in rows]),
                         luecke=stat([r["gap"] for r in rows if not math.isnan(r["gap"])]) if any(not math.isnan(r["gap"]) for r in rows) else None)
    return dict(instanzen=[dict(n=n, k=k, L=length, seed=seed) for n, k, length, seed in ABLATION_INSTANCES], varianten=out)


def part_c(limit):
    out = []
    for n, k, length in SCALING:
        rows = []
        for seed in SCALING_SEEDS:
            coords, demand = instance(n, seed)
            hint = demand_greedy_construction(coords, demand, k, length)
            g = evaluate_network(hint, demand)
            r = C.solve_cpsat(demand, k, length, time_limit=limit, hint_lines=hint)
            rows.append(dict(proven=r.proven, secs=r.seconds, gap=r.gap_pp, cp=r.stats["direct_pct"], greedy=g["direct_pct"], bound=r.bound_direct_pct, unreach=r.stats["unreachable_pct"],
                             stage1=r.nodes_stage[0][0] == "OPTIMAL"))
            print("C", n, k, length, seed, r.status, "%.1fs" % r.seconds, "gap %.2f" % r.gap_pp, flush=True)
        out.append(dict(n=n, k=k, L=length, bewiesen=share([r["proven"] for r in rows]), erreichbarkeit_bewiesen=share([r["stage1"] for r in rows]), sekunden=stat([r["secs"] for r in rows]),
                        luecke_pp=stat([r["gap"] for r in rows]), cpsat_direkt=stat([r["cp"] for r in rows]), greedy_direkt=stat([r["greedy"] for r in rows]),
                        verbesserung_gegen_greedy=stat([r["cp"] - r["greedy"] for r in rows]), schranke=stat([r["bound"] for r in rows]),
                        greedy_hoechstens_unter_optimum=stat([r["bound"] - r["greedy"] for r in rows]), ohne_unerreichbar=share([r["unreach"] < 1e-9 for r in rows])))
    return out


def main(limit=30.0):
    t0 = time.time()
    res = dict(meta=dict(zeitlimit_s=limit, workers=C.default_workers(), maschine=platform.processor(), system=platform.platform(), python=platform.python_version(),
                         ortools=__import__("ortools").__version__, seeds_skalierung="1-10", hub_concentration=HUB, n_hubs=N_HUBS,
                         hinweis="Zeiten auf einem Entwicklungsrechner, andere Prozesse laufen ggf. parallel; Streamlit Cloud nicht gemessen"))
    res["uebereinstimmung"] = part_a(limit)
    res["ablation"] = part_b(limit)
    res["skalierung"] = part_c(limit)
    res["meta"]["sekunden_gesamt"] = round(time.time() - t0)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(rnd(res), fh, ensure_ascii=False, separators=(",", ":"))
    print("geschrieben:", OUT, "%.0f kB" % (os.path.getsize(OUT) / 1024.0), "in %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 30.0)
