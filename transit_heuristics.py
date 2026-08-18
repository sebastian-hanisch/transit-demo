"""
Zwei selbst implementierte Heuristiken für das Liniennetz-Design-Problem:

- star_network_construction: wählt die nachfragestärkste Haltestelle als
  zentralen Hub und baut radiale Linien nach außen (Polarwinkel-Sektoren um
  den Hub, analog zum Sweep-Verfahren der Tourenplanung-Demo). Repräsentiert
  ein historisch gewachsenes, rein geometrisches Sternnetz - einfach und
  nachvollziehbar, aber nicht an der tatsächlichen Nachfrage ausgerichtet.
  Dient als Baseline.

- demand_greedy_construction: baut Linien entlang der stärksten noch
  unbedienten Nachfrage-Korridore, erweitert jede Linie greedy um die
  Haltestelle mit dem größten zusätzlichen Nachfragebeitrag. Folgt echten
  Nachfragemustern statt reiner Geometrie.

Beide geben eine Liste von Linien zurück, jede Linie eine Liste von
Haltestellen-Indizes in Fahrtreihenfolge.
"""

import numpy as np


def star_network_construction(coords, demand, n_lines, max_line_length):
    """Sternnetz-Baseline: Hub = nachfragestärkste Haltestelle, restliche
    Haltestellen per Polarwinkel um den Hub in n_lines Sektoren geteilt, je
    Sektor eine vom Hub nach außen führende Linie (Haltestellen nach
    Distanz vom Hub sortiert)."""
    n = len(coords)
    if n == 0:
        return [[] for _ in range(n_lines)]

    total_demand_per_stop = demand.sum(axis=1)
    hub = int(np.argmax(total_demand_per_stop))

    other_stops = [i for i in range(n) if i != hub]
    if not other_stops:
        return [[hub] for _ in range(n_lines)]

    angles = np.arctan2(
        coords[other_stops, 1] - coords[hub, 1],
        coords[other_stops, 0] - coords[hub, 0],
    )
    order = np.argsort(angles)
    sorted_by_angle = [other_stops[i] for i in order]

    n_lines_eff = max(1, min(n_lines, len(sorted_by_angle)))
    lines = []
    chunk_size = len(sorted_by_angle) / n_lines_eff
    for k in range(n_lines_eff):
        start = int(round(k * chunk_size))
        end = int(round((k + 1) * chunk_size))
        sector_stops = sorted_by_angle[start:end]
        sector_stops.sort(key=lambda s: float(np.linalg.norm(coords[s] - coords[hub])))
        line = [hub] + sector_stops[: max(0, max_line_length - 1)]
        lines.append(line)
    while len(lines) < n_lines:
        lines.append([hub])
    return lines


def demand_greedy_construction(coords, demand, n_lines, max_line_length, growth_bonus=2.5):
    """Nachfrage-getriebene Liniengenerierung: startet jede neue Linie am
    stärksten noch nicht direkt bedienten Haltestellenpaar und erweitert sie
    an beiden Enden greedy um die Haltestelle mit dem größten zusätzlichen
    Nachfragebeitrag, bis max_line_length erreicht ist oder kein Gewinn mehr
    möglich ist.

    Zwei Korrekturen gegenüber einer naiven reinen Nachfrage-Gier (beide im
    Benchmark als notwendig verifiziert, siehe README):
    1. Ab der zweiten Linie muss das Startpaar mindestens eine bereits im
       Netz enthaltene Haltestelle einschließen - erzwingt ein
       zusammenhängendes Netz statt isolierter Teilnetze.
    2. Ein Wachstumsbonus bevorzugt noch nicht abgedeckte Haltestellen bei
       Start- und Erweiterungsentscheidungen - ohne ihn konzentriert sich
       die Konstruktion immer wieder auf dieselben wenigen nachfragestarken
       Haltestellen und deckt nur einen Bruchteil des Netzes ab (empirisch
       gefunden: 11 von 20 Haltestellen statt aller 20)."""
    n = len(coords)
    lines = []
    covered_pairs = set()
    network_stops = set()

    for line_num in range(n_lines):
        best_pair, best_score = None, -1.0
        best_pair_demand = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                if (i, j) in covered_pairs:
                    continue
                i_in, j_in = i in network_stops, j in network_stops
                if line_num > 0 and not (i_in or j_in):
                    continue  # würde ein unangebundenes Teilnetz erzeugen
                d = demand[i][j]
                score = d
                if line_num > 0 and (i_in != j_in):
                    score *= growth_bonus  # genau eine Haltestelle ist neu -> Netz waechst
                if score > best_score:
                    best_score = score
                    best_pair = (i, j)
                    best_pair_demand = d
        if best_pair is None or best_pair_demand <= 0:
            break

        line = list(best_pair)
        while len(line) < max_line_length:
            best_ext, best_ext_score = None, 0.0
            for candidate in range(n):
                if candidate in line:
                    continue
                gain = sum(demand[candidate][s] for s in line)
                score = gain * (growth_bonus if candidate not in network_stops else 1.0)
                if score > best_ext_score:
                    best_ext_score = score
                    best_ext = candidate
            if best_ext is None:
                break
            d_front = float(np.linalg.norm(coords[best_ext] - coords[line[0]]))
            d_back = float(np.linalg.norm(coords[best_ext] - coords[line[-1]]))
            if d_front <= d_back:
                line.insert(0, best_ext)
            else:
                line.append(best_ext)

        lines.append(line)
        network_stops.update(line)
        for a in range(len(line)):
            for b in range(a + 1, len(line)):
                covered_pairs.add(tuple(sorted((line[a], line[b]))))

    while len(lines) < n_lines:
        lines.append([])
    return lines
