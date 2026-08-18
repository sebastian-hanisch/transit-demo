"""
Erzeugt Haltestellen (2D-Koordinaten) und eine Nachfragematrix zwischen allen
Haltestellenpaaren. Die Nachfrage ist symmetrisch (demand[i][j] == demand[j][i]
- repräsentiert aggregierte Tagesnachfrage in beide Richtungen, für die
Liniennetz-Gestaltung ausreichend, da Linien ohnehin in beide Richtungen
befahren werden) und kann mehr oder weniger stark auf einzelne "Hub"-
Haltestellen konzentriert sein (Pendler-Muster: viele Fahrten von/zu einem
zentralen Bahnhof oder Stadtzentrum statt gleichverteilt).
"""

import numpy as np


def generate_stops_and_demand(n_stops, seed, hub_concentration=0.5, n_hubs=2):
    """Erzeugt n_stops zufällige 2D-Koordinaten und eine symmetrische
    Nachfragematrix.

    hub_concentration: 0.0 = Nachfrage gleichverteilt über alle Paare,
    höhere Werte (bis 1.0) = ein wachsender Anteil der Nachfrage konzentriert
    sich auf Fahrten von/zu den n_hubs nachfragestärksten Haltestellen
    (Pendler-/Sternmuster, wie es in vielen realen Städten vorkommt).

    Gibt (coords, demand, hub_idxs) zurück. demand[i][i] ist immer 0 (keine
    Nachfrage von einer Haltestelle zu sich selbst).
    """
    rng = np.random.default_rng(seed)
    coords = rng.uniform(5, 95, size=(n_stops, 2))

    base = rng.uniform(1, 10, size=(n_stops, n_stops))
    base = (base + base.T) / 2  # symmetrisch machen

    n_hubs_eff = max(1, min(n_hubs, n_stops))
    hub_idxs = rng.choice(n_stops, size=n_hubs_eff, replace=False)

    multiplier = np.ones((n_stops, n_stops))
    boost = 1.0 + hub_concentration * 6.0
    for h in hub_idxs:
        multiplier[h, :] *= boost
        multiplier[:, h] *= boost

    demand = base * multiplier
    np.fill_diagonal(demand, 0.0)
    demand = demand.round(0)
    return coords, demand, hub_idxs
