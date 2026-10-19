"""Messreihe zum Exakt-Tab: beide Heuristiken gegen das exakte Optimum (vollständige Aufzählung) auf kleinen Instanzen.

Aufruf:  python -B tools/sweep_exact.py [Prozesse]     (Standard 4)
Je Konfiguration (Haltestellen, Linien, max. Länge) die Zufalls-Seeds 1 bis 100, Pendler-Konzentration 0,5, zwei Hubs. Ergebnis: data/exact_results.json
(Statistikfelder {n, mean, se, med, p10, p90}, Anteile {k, n, p}); keine Rohdaten."""
import json
import math
import os
import sys
import time
from multiprocessing import Pool

sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402

import transit_exact as X  # noqa: E402
from transit_demand import generate_stops_and_demand  # noqa: E402
from transit_evaluation import evaluate_network  # noqa: E402
from transit_heuristics import demand_greedy_construction, star_network_construction  # noqa: E402

CONFIGS = [(8, 3, 5), (9, 2, 4), (10, 3, 5)]
SEEDS = list(range(1, 101))
HUB, N_HUBS = 0.5, 2
OUT = os.path.join(ROOT, "data", "exact_results.json")


def lex(stats):
    return (round(stats["unreachable_demand"], 6), -round(stats["direct_demand"], 6))


def one(job):
    n, k, length, seed = job
    coords, demand, _ = generate_stops_and_demand(n, seed, HUB, N_HUBS)
    ex = X.solve_exact(coords, demand, k, length)
    row = dict(n=n, k=k, L=length, seed=seed, combos=ex.n_combinations, secs=ex.seconds, exact_lex=ex.stats_lex, exact_dir=ex.stats_direct)
    for name, fn in (("star", star_network_construction), ("greedy", demand_greedy_construction)):
        st = evaluate_network(fn(coords, demand, k, length), demand)
        row[name] = st
        row[name + "_hit"] = lex(st) == lex(ex.stats_lex)
    return row


def stat(xs):
    a = np.asarray(xs, float)
    return dict(n=int(len(a)), mean=float(a.mean()), se=float(a.std(ddof=1) / math.sqrt(len(a))), med=float(np.median(a)), p10=float(np.percentile(a, 10)), p90=float(np.percentile(a, 90)))


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


def main(procs=4):
    jobs = [(n, k, length, s) for (n, k, length) in CONFIGS for s in SEEDS]
    t0 = time.time()
    with Pool(procs) as pool:
        rows = pool.map(one, jobs, chunksize=4)
    out = {"meta": dict(seeds="1-100", hub_concentration=HUB, n_hubs=N_HUBS, configs=[dict(n=n, k=k, L=length) for n, k, length in CONFIGS],
                        zielgroesse="Auswahlregel der App: kleinste nicht erreichbare, dann größte direkte Nachfrage; Optimum durch vollständige Aufzählung (transit_exact.py)",
                        sekunden=round(time.time() - t0, 1)), "konfigurationen": []}
    for (n, k, length) in CONFIGS:
        sel = [r for r in rows if (r["n"], r["k"], r["L"]) == (n, k, length)]
        cfg = dict(n=n, k=k, L=length, combos=sel[0]["combos"], solve_seconds=stat([r["secs"] for r in sel]),
                   exakt=dict(direct=stat([r["exact_lex"]["direct_pct"] for r in sel]), unreachable=stat([r["exact_lex"]["unreachable_pct"] for r in sel]),
                              ohne_unerreichbar=share([r["exact_lex"]["unreachable_pct"] < 1e-9 for r in sel]),
                              direct_obere_schranke=stat([r["exact_dir"]["direct_pct"] for r in sel])))
        for name in ("star", "greedy"):
            cfg[name] = dict(direct=stat([r[name]["direct_pct"] for r in sel]), unreachable=stat([r[name]["unreachable_pct"] for r in sel]),
                             ohne_unerreichbar=share([r[name]["unreachable_pct"] < 1e-9 for r in sel]), optimum_getroffen=share([r[name + "_hit"] for r in sel]),
                             luecke_direkt_zur_oberen_schranke=stat([r["exact_dir"]["direct_pct"] - r[name]["direct_pct"] for r in sel]),
                             luecke_direkt_zum_optimum=stat([r["exact_lex"]["direct_pct"] - r[name]["direct_pct"] for r in sel]),
                             nie_besser_als_optimum=share([lex(r[name]) >= lex(r["exact_lex"]) for r in sel]))
        cfg["greedy_besser_als_star_direkt"] = share([r["greedy"]["direct_pct"] > r["star"]["direct_pct"] for r in sel])
        out["konfigurationen"].append(cfg)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(rnd(out), fh, ensure_ascii=False, separators=(",", ":"))
    print("geschrieben:", OUT, "%.0f kB" % (os.path.getsize(OUT) / 1024.0), "in %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 4)
