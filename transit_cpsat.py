"""
CP-SAT-Modell (OR-Tools) für das Liniennetz-Design: dasselbe Problem wie die Aufzählung in `transit_exact.py`, aber für mehr Haltestellen.

Entscheidung: x[l][s] = 1, wenn Haltestelle s auf Linie l liegt (höchstens bzw. genau `L` Haltestellen je Linie, `k` Linien).
Ein Paar (i, j) mit Nachfrage w ist *direkt* erreichbar, wenn eine Linie beide Haltestellen enthält, und *erreichbar* (höchstens ein Umstieg), wenn eine Linie a die
Haltestelle i enthält und j auf einer Linie liegt, die a schneidet (oder auf a selbst). Zielgröße wie in der Primäransicht: erst die kleinste nicht erreichbare
Nachfrage, dann die größte direkte Nachfrage (lexikografisch). Das Modell maximiert nur, deshalb genügen Obergrenzen (Implikationen) statt voller Äquivalenzen.

Modellverbesserungen (jede einzeln abschaltbar, `ModelOptions`; Wirkung gemessen in `tools/sweep_cpsat.py`):
- exact_size: Jede Linie hat genau min(L, n) Haltestellen (mehr Haltestellen schaden nie: dieselbe Dominanz wie bei der Aufzählung).
- lex_symmetry: Die k Linien sind austauschbar; eine strenge lexikografische Ordnung der Haltestellen-Bitmasken lässt je Netz nur eine Anordnung zu (k! Mal weniger Symmetrie).
- compact_reach: Statt je Paar und Linienpaar eine Hilfsvariable (k·(k−1)·Paare) gibt es je Linie und Haltestelle eine Variable N[a][j] („j liegt auf a oder einer Linie, die a schneidet“,
  k·n Variablen); ein Paar ist erreichbar, wenn eine Linie i enthält und N[a][j] gilt.
- hint: Das Netz der Heuristiken (aufgefüllt auf volle Länge, passend geordnet) als Startlösung.
- line_cuts: Je Linie höchstens m − 1 Paare je Haltestelle und m (m − 1) / 2 Paare insgesamt (verschärft die lineare Relaxation, die sonst bei x = 1/2 sehr schwach ist).
- two_stage: erst die erreichbare Nachfrage maximieren, dann bei festgehaltener erreichbarer Nachfrage die direkte: Die Schranke der zweiten Stufe ist dann in Prozentpunkten
  der direkten Nachfrage lesbar (bei der gewichteten Summe wird sie von der Erreichbarkeit dominiert).
"""

import math
import os
import time
from dataclasses import dataclass

from ortools.sat.python import cp_model

from transit_evaluation import evaluate_network


@dataclass(frozen=True)
class ModelOptions:
    exact_size: bool = True
    lex_symmetry: bool = True
    compact_reach: bool = True
    hint: bool = True
    two_stage: bool = True
    line_cuts: bool = True


@dataclass
class CpSatResult:
    status: str              # OPTIMAL (bewiesen) oder FEASIBLE (beste gefundene Lösung) oder UNKNOWN
    proven: bool
    lines: list
    stats: dict              # evaluate_network des Netzes (unabhängig vom Modell gerechnet)
    reach_demand: float
    direct_demand: float
    total_demand: float
    bound_direct_pct: float  # obere Schranke der direkten Nachfrage in % der Gesamtnachfrage (bei bewiesener erster Stufe)
    gap_pp: float            # Schranke minus erreichter Wert in Prozentpunkten der direkten Nachfrage
    seconds: float
    nodes_stage: list        # je Stufe: (Status, Sekunden)


def default_workers():
    return max(1, min(8, os.cpu_count() or 1))


def _pairs(demand):
    n = demand.shape[0]
    return [(i, j, int(round(float(demand[i][j])))) for i in range(n) for j in range(i + 1, n) if demand[i][j] > 0]


def _pad_hint(hint_lines, demand, k, m):
    """Heuristik-Netz als Startlösung: jede Linie auf m Haltestellen auffüllen (um die Haltestellen mit der größten Nachfrage zur Linie), k Linien, absteigend nach Bitmaske."""
    n = demand.shape[0]
    lines = []
    for line in list(hint_lines)[:k]:
        cur = list(dict.fromkeys(line))[:m]
        while len(cur) < m:
            best = max((s for s in range(n) if s not in cur), key=lambda s: (sum(float(demand[s][t]) for t in cur), -s))
            cur.append(best)
        lines.append(cur)
    while len(lines) < k:
        lines.append(list(range(m)))
    return sorted(lines, key=lambda l: -sum(1 << s for s in l))


def build_model(demand, k, L, opts=ModelOptions(), stage="lex", reach_floor=None, hint_lines=None):
    """Baut das Modell. stage: 'lex' (gewichtete Summe), 'reach' (erreichbare Nachfrage maximieren) oder 'direct' (direkte Nachfrage maximieren unter reach >= reach_floor)."""
    n = demand.shape[0]
    pairs = _pairs(demand)
    total = sum(w for _, _, w in pairs)
    m_size = min(L, n)
    mdl = cp_model.CpModel()
    x = [[mdl.NewBoolVar(f"x{l}_{s}") for s in range(n)] for l in range(k)]
    for l in range(k):
        if opts.exact_size:
            mdl.Add(sum(x[l]) == m_size)
        else:
            mdl.Add(sum(x[l]) <= m_size)
    if opts.lex_symmetry and k > 1:
        distinct = math.comb(n, m_size) >= k
        for l in range(k - 1):
            a = sum((1 << s) * x[l][s] for s in range(n))
            b = sum((1 << s) * x[l + 1][s] for s in range(n))
            mdl.Add(a >= b + (1 if distinct else 0))

    # gemeinsame Haltestelle zweier Linien
    share = {}
    for a in range(k):
        for b in range(a + 1, k):
            vs = []
            for s in range(n):
                v = mdl.NewBoolVar(f"v{a}_{b}_{s}")
                mdl.AddImplication(v, x[a][s])
                mdl.AddImplication(v, x[b][s])
                vs.append(v)
            c = mdl.NewBoolVar(f"c{a}_{b}")
            mdl.Add(c <= sum(vs))
            share[a, b] = share[b, a] = c

    reach_vars, direct_vars = [], []
    u_by_line = [[] for _ in range(k)]               # (Paar-Index, u-Variable) je Linie, für die Schnittbedingungen
    if opts.compact_reach:
        N = [[mdl.NewBoolVar(f"N{a}_{j}") for j in range(n)] for a in range(k)]       # j liegt auf a oder auf einer Linie, die a schneidet
        for a in range(k):
            for j in range(n):
                terms = [x[a][j]]
                for b in range(k):
                    if b != a:
                        y = mdl.NewBoolVar(f"y{a}_{b}_{j}")
                        mdl.AddImplication(y, share[a, b])
                        mdl.AddImplication(y, x[b][j])
                        terms.append(y)
                mdl.Add(N[a][j] <= sum(terms))
    for p, (i, j, w) in enumerate(pairs):
        us = []
        for l in range(k):
            u = mdl.NewBoolVar(f"u{l}_{p}")
            mdl.AddImplication(u, x[l][i])
            mdl.AddImplication(u, x[l][j])
            us.append(u)
            u_by_line[l].append((p, u))
        d = mdl.NewBoolVar(f"d{p}")
        mdl.Add(d <= sum(us))
        if opts.compact_reach:
            ws = []
            for a in range(k):
                wv = mdl.NewBoolVar(f"w{a}_{p}")
                mdl.AddImplication(wv, x[a][i])
                mdl.AddImplication(wv, N[a][j])
                ws.append(wv)
            r = mdl.NewBoolVar(f"r{p}")
            mdl.Add(r <= sum(ws))
        else:
            ts = []
            for a in range(k):
                for b in range(k):
                    if a != b:
                        t = mdl.NewBoolVar(f"t{a}_{b}_{p}")
                        mdl.AddImplication(t, x[a][i])
                        mdl.AddImplication(t, x[b][j])
                        mdl.AddImplication(t, share[a, b])
                        ts.append(t)
            r = mdl.NewBoolVar(f"r{p}")
            mdl.Add(r <= sum(us) + sum(ts))
        mdl.AddImplication(d, r)
        direct_vars.append(d)
        reach_vars.append(r)

    if opts.line_cuts:
        # Eine Linie mit m Haltestellen enthält höchstens m − 1 Paare je Haltestelle und höchstens m (m − 1) / 2 Paare: verschärft die LP-Relaxation
        for l in range(k):
            for sidx in range(n):
                ps = [u for (p, u) in u_by_line[l] if sidx in (pairs[p][0], pairs[p][1])]
                if ps:
                    mdl.Add(sum(ps) <= (m_size - 1) * x[l][sidx])
            mdl.Add(sum(u for _, u in u_by_line[l]) <= m_size * (m_size - 1) // 2)
    reach_sum = sum(w * r for (_, _, w), r in zip(pairs, reach_vars))
    direct_sum = sum(w * d for (_, _, w), d in zip(pairs, direct_vars))
    if stage == "lex":
        mdl.Maximize(reach_sum * (total + 1) + direct_sum)
    elif stage == "reach":
        mdl.Maximize(reach_sum)
    elif stage == "direct":
        mdl.Add(reach_sum >= int(reach_floor))
        mdl.Maximize(direct_sum)
    else:
        raise ValueError(stage)
    if opts.hint and hint_lines is not None and opts.exact_size:
        for l, line in enumerate(_pad_hint(hint_lines, demand, k, m_size)):
            for s in range(n):
                mdl.AddHint(x[l][s], 1 if s in line else 0)
    return mdl, x, total


def _run(mdl, limit, workers, seed=1):
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(limit)
    solver.parameters.num_workers = workers
    solver.parameters.random_seed = seed
    t0 = time.perf_counter()
    status = solver.Solve(mdl)
    return solver, status, time.perf_counter() - t0


def _lines_of(solver, x, n):
    return [[s for s in range(n) if solver.Value(x[l][s])] for l in range(len(x))]


def solve_cpsat(demand, k, L, time_limit=10.0, workers=None, opts=ModelOptions(), hint_lines=None):
    """Löst das Modell (zweistufig oder gewichtet je nach `opts`) mit Zeitlimit; das Limit gilt für die gesamte Rechnung."""
    t0 = time.perf_counter()
    workers = workers or default_workers()
    n = demand.shape[0]
    stages = []
    if opts.two_stage:
        mdl1, x1, total = build_model(demand, k, L, opts, "reach", hint_lines=hint_lines)
        solver1, st1, sec1 = _run(mdl1, time_limit * 0.4, workers)
        stages.append((solver1.StatusName(st1), sec1))
        if st1 not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return CpSatResult("UNKNOWN", False, [], {}, 0.0, 0.0, float(total), 100.0, 100.0, time.perf_counter() - t0, stages)
        floor_reach = round(solver1.ObjectiveValue())
        bound_reach = solver1.BestObjectiveBound()
        mdl2, x2, _ = build_model(demand, k, L, opts, "direct", reach_floor=floor_reach, hint_lines=_lines_of(solver1, x1, n))
        solver2, st2, sec2 = _run(mdl2, max(1.0, time_limit - (time.perf_counter() - t0)), workers)
        stages.append((solver2.StatusName(st2), sec2))
        if st2 not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            solver, x, st = solver1, x1, st1               # zweite Stufe ohne Lösung: die der ersten behalten
            bound_direct = float(total)
        else:
            solver, x, st = solver2, x2, st2
            bound_direct = solver2.BestObjectiveBound()
        proven = st1 == cp_model.OPTIMAL and st2 == cp_model.OPTIMAL
        # Schranke der direkten Nachfrage nur dann aussagekräftig, wenn die erreichbare Nachfrage bewiesen optimal ist
        if st1 != cp_model.OPTIMAL:
            bound_direct = float(total)
    else:
        mdl, x, total = build_model(demand, k, L, opts, "lex", hint_lines=hint_lines)
        solver, st, sec = _run(mdl, time_limit, workers)
        stages.append((solver.StatusName(st), sec))
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return CpSatResult("UNKNOWN", False, [], {}, 0.0, 0.0, float(total), 100.0, 100.0, time.perf_counter() - t0, stages)
        proven = st == cp_model.OPTIMAL
        # Zielwert = erreichbar · (Gesamt + 1) + direkt: bei bewiesenem Optimum steht die direkte Nachfrage im Rest; sonst ist keine Schranke bekannt
        bound_direct = float(round(solver.ObjectiveValue()) % (total + 1)) if proven else float(total)
    lines = _lines_of(solver, x, n)
    stats = evaluate_network(lines, demand)
    total_f = float(total)
    direct_pct = stats["direct_demand"] / total_f * 100 if total_f else 0.0
    bound_pct = min(100.0, bound_direct / total_f * 100) if total_f else 0.0
    return CpSatResult("OPTIMAL" if proven else "FEASIBLE", proven, lines, stats, stats["direct_demand"] + stats["one_transfer_demand"], stats["direct_demand"], total_f, bound_pct,
                       max(0.0, bound_pct - direct_pct), time.perf_counter() - t0, stages)
