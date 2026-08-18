"""
Bewertet ein Liniennetz gegen eine Nachfragematrix: für jedes Haltestellenpaar
mit Nachfrage > 0 wird geprüft, ob es direkt (beide Haltestellen auf
derselben Linie), mit einem Umstieg (zwei Linien mit gemeinsamer Haltestelle)
oder gar nicht innerhalb eines Umstiegs erreichbar ist - die zentrale, neue
Bewertungslogik dieser Demo (anders als bei der Touren- oder Packungsdemo).
"""

from collections import defaultdict


def evaluate_network(lines, demand):
    """Gibt ein Dict mit nachfragegewichteten Anteilen zurück: direct_pct,
    one_transfer_pct, unreachable_pct (in %, summieren sich zu 100), sowie
    die absoluten Nachfragewerte und total_demand."""
    n_stops = demand.shape[0]

    lines_by_stop = defaultdict(set)
    for line_idx, line in enumerate(lines):
        for s in line:
            lines_by_stop[s].add(line_idx)
    line_sets = [set(line) for line in lines]

    direct_demand = 0.0
    one_transfer_demand = 0.0
    unreachable_demand = 0.0
    total_demand = 0.0

    for i in range(n_stops):
        for j in range(i + 1, n_stops):
            d = float(demand[i][j])
            if d <= 0:
                continue
            total_demand += d

            lines_i = lines_by_stop.get(i, set())
            lines_j = lines_by_stop.get(j, set())

            if lines_i & lines_j:
                direct_demand += d
                continue

            found_transfer = False
            for la in lines_i:
                for lb in lines_j:
                    if line_sets[la] & line_sets[lb]:
                        found_transfer = True
                        break
                if found_transfer:
                    break

            if found_transfer:
                one_transfer_demand += d
            else:
                unreachable_demand += d

    if total_demand <= 0:
        return {
            "direct_pct": 0.0, "one_transfer_pct": 0.0, "unreachable_pct": 0.0,
            "total_demand": 0.0, "direct_demand": 0.0, "one_transfer_demand": 0.0,
            "unreachable_demand": 0.0,
        }

    return {
        "direct_pct": direct_demand / total_demand * 100,
        "one_transfer_pct": one_transfer_demand / total_demand * 100,
        "unreachable_pct": unreachable_demand / total_demand * 100,
        "total_demand": total_demand,
        "direct_demand": direct_demand,
        "one_transfer_demand": one_transfer_demand,
        "unreachable_demand": unreachable_demand,
    }


def stops_with_unreachable_demand(lines, demand):
    """Gibt die Menge der Haltestellen-Indizes zurück, die mindestens eine
    Nachfragebeziehung haben, die weder direkt noch mit einem Umstieg
    erreichbar ist - zur visuellen Hervorhebung auf der Karte."""
    n_stops = demand.shape[0]
    lines_by_stop = defaultdict(set)
    for line_idx, line in enumerate(lines):
        for s in line:
            lines_by_stop[s].add(line_idx)
    line_sets = [set(line) for line in lines]

    affected = set()
    for i in range(n_stops):
        for j in range(i + 1, n_stops):
            if demand[i][j] <= 0:
                continue
            lines_i = lines_by_stop.get(i, set())
            lines_j = lines_by_stop.get(j, set())
            if lines_i & lines_j:
                continue
            found_transfer = any(line_sets[la] & line_sets[lb] for la in lines_i for lb in lines_j)
            if not found_transfer:
                affected.add(i)
                affected.add(j)
    return affected


def stops_covered(lines, n_stops):
    """Wie viele der n_stops Haltestellen liegen auf mindestens einer Linie
    (unabhängig von Nachfrage) - ergänzende, einfachere Kennzahl."""
    covered = set()
    for line in lines:
        covered.update(line)
    return len(covered & set(range(n_stops)))
