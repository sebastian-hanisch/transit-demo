"""
Liniennetz-Design (öffentlicher Nahverkehr) – interaktive Demo
Sebastian Hanisch - Operations Research und Machine Learning

Hinweis zur Einordnung: Die dokumentierten Kernspezialisierungen liegen im
Fracht-/Logistikbereich (Tourenplanung, Container-/Palettenpackung,
Wechselbrücken-Hofmanagement), nicht speziell im ÖPNV. Diese Demo zeigt
dieselbe Methodik (Konstruktionsheuristik + Bewertung + Vergleich) auf ein
neues Feld angewendet, nicht jahrelange Nahverkehrs-Facherfahrung.

Von Anfang an mit der Lehre aus der Tourenplanung-Demo gebaut: Ergebnis
zuerst zeigen ("Ihr optimiertes Liniennetz"), Methodenvergleich sekundär im
Expander - nicht erst nachträglich umstrukturiert.

Lauffähig mit: streamlit run app.py
"""

import pandas as pd
import streamlit as st

from transit_demand import generate_stops_and_demand
from transit_evaluation import evaluate_network, stops_with_unreachable_demand
from transit_heuristics import demand_greedy_construction, star_network_construction
from transit_pdf_export import generate_network_plan_pdf
from transit_presets import apply_preset, bounds, init_session_state_defaults, load_permalink_settings, randomize_seed, sync_query_params
from transit_ui_panel import render_network_panel
from transit_visualization import build_network_figure

st.set_page_config(page_title="Liniennetz-Design – Sebastian Hanisch", layout="wide")

st.title("🚌 Liniennetz-Design für den öffentlichen Nahverkehr")
st.markdown(
    """
Interaktive Demo zur Gestaltung eines Buslinien-Netzes anhand einer Fahrgast-
Nachfragematrix. Zwei selbst implementierte Ansätze – ein **Sternnetz** (radial vom
nachfragestärksten Knotenpunkt, wie viele historisch gewachsene Netze) und eine
**nachfrage-optimierte Liniengenerierung** (folgt den stärksten Nachfrage-Korridoren) –
werden direkt verglichen. Anders als bei Kosten-getriebener Tourenplanung zählt hier vor
allem eine Kennzahl: Wie viele Fahrgäste erreichen ihr Ziel ohne Umzusteigen?
"""
)

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
preset_col1, preset_col2, preset_col3 = st.columns(3)
with preset_col1:
    st.button(
        "🏙️ Kompaktstadt", width="stretch",
        on_click=apply_preset, args=(18, 4, 6, 0.3, 1, 5),
        help="Kleines, dicht bebautes Gebiet mit eher gleichverteilter Nachfrage.",
    )
with preset_col2:
    st.button(
        "🚉 Pendlerstadt", width="stretch",
        on_click=apply_preset, args=(25, 5, 8, 0.8, 1, 12),
        help="Starke Konzentration der Nachfrage auf einen zentralen Bahnhof/Hub - klassisches Pendlermuster.",
    )
with preset_col3:
    st.button(
        "🌆 Mehrere Zentren", width="stretch",
        on_click=apply_preset, args=(30, 6, 7, 0.6, 3, 8),
        help="Größere Stadt mit mehreren Nachfrage-Zentren statt nur einem.",
    )

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    n_stops = st.slider("Anzahl Haltestellen", *bounds("n_stops_slider"), key="n_stops_slider")
    n_lines = st.slider("Anzahl Linien", *bounds("n_lines_slider"), key="n_lines_slider")
    max_line_length = st.slider(
        "Max. Haltestellen je Linie", *bounds("max_line_length_slider"), key="max_line_length_slider",
    )

    st.markdown("**Nachfragemuster**")
    hub_concentration = st.slider(
        "Pendler-Konzentration", *bounds("hub_concentration_slider"), step=0.05, key="hub_concentration_slider",
        help="0 = Nachfrage gleichverteilt über alle Haltestellenpaare, 1 = stark auf wenige Hub-Haltestellen konzentriert (Pendlermuster).",
    )
    n_hubs = st.slider("Anzahl Nachfrage-Hubs", *bounds("n_hubs_slider"), key="n_hubs_slider")
    seed = st.number_input("Zufalls-Seed", step=1, key="seed_input")

    st.button(
        "🎲 Neues Szenario generieren", width="stretch", on_click=randomize_seed,
        help="Würfelt einen neuen Zufalls-Seed und erzeugt damit ein komplett neues Szenario - "
        "praktisch, ohne selbst eine neue Seed-Zahl eintippen zu müssen.",
    )

sync_query_params(n_stops, n_lines, max_line_length, hub_concentration, n_hubs, seed)

if "force_regen" not in st.session_state:
    st.session_state.force_regen = False

gen_key = (n_stops, n_lines, max_line_length, hub_concentration, n_hubs, int(seed))
needs_init = (
    "gen_key_cache" not in st.session_state or st.session_state.force_regen
    or st.session_state.get("gen_key_cache") != gen_key
)
if needs_init:
    coords, demand, hub_idxs = generate_stops_and_demand(
        n_stops, int(seed), hub_concentration=hub_concentration, n_hubs=n_hubs
    )
    st.session_state.coords = coords
    st.session_state.demand = demand
    st.session_state.hub_idxs = hub_idxs
    st.session_state.gen_key_cache = gen_key
    st.session_state.force_regen = False

coords = st.session_state.coords
demand = st.session_state.demand
hub_idxs = st.session_state.hub_idxs
ids = list(range(1, n_stops + 1))

with st.expander("📍 Haltestellen (nicht editierbar – Nachfrage ist an die Generierung gekoppelt)"):
    total_demand_per_stop = demand.sum(axis=1)
    stops_df = pd.DataFrame({
        "ID": ids,
        "x": coords[:, 0].round(1),
        "y": coords[:, 1].round(1),
        "Gesamtnachfrage": total_demand_per_stop.round(0),
        "Hub": ["⭐" if i in hub_idxs else "" for i in range(n_stops)],
    })
    st.dataframe(stops_df, width="stretch", hide_index=True)

lines_star = star_network_construction(coords, demand, n_lines, max_line_length)
lines_greedy = demand_greedy_construction(coords, demand, n_lines, max_line_length)

stats_star = evaluate_network(lines_star, demand)
stats_greedy = evaluate_network(lines_greedy, demand)

# Beste der beiden Methoden fuer die Primaeransicht: zuerst wenigste
# unerreichbare Nachfrage, dann meiste direkte (umstiegsfreie) Erreichbarkeit.
candidates = [
    {"key": "star", "label": "Sternnetz", "lines": lines_star, **stats_star},
    {"key": "greedy", "label": "Nachfrage-optimiert", "lines": lines_greedy, **stats_greedy},
]
best = min(candidates, key=lambda c: (c["unreachable_pct"], -c["direct_pct"]))
baseline = next(c for c in candidates if c["key"] != best["key"])

st.markdown("## 🎯 Ihr optimiertes Liniennetz")

direct_gain = best["direct_pct"] - baseline["direct_pct"]
unreachable_diff = best["unreachable_pct"] - baseline["unreachable_pct"]

m1, m2, m3 = st.columns(3)
m1.metric(
    "Ohne Umstieg erreichbar", f"{best['direct_pct']:.1f}%",
    delta=f"{direct_gain:+.1f} Pp. ggü. Alternative",
)
m2.metric("Mit 1 Umstieg erreichbar", f"{best['one_transfer_pct']:.1f}%")
m3.metric(
    "Nicht erreichbar", f"{best['unreachable_pct']:.1f}%",
    delta=f"{unreachable_diff:+.1f} Pp. ggü. Alternative", delta_color="inverse",
)

if direct_gain > 1.0:
    st.success(
        f"💡 Mit nachfrage-optimierter Liniengestaltung erreichen **{best['direct_pct']:.1f}%** Ihrer "
        f"Fahrgäste ihr Ziel ohne Umzusteigen – **{direct_gain:.1f} Prozentpunkte mehr** als bei "
        f"'{baseline['label']}'. Weniger Umstiege bedeuten kürzere Reisezeiten und in der Regel "
        f"höhere Fahrgastzufriedenheit und Auslastung."
    )

fig_best = build_network_figure(coords, best["lines"], hub_idxs, highlight_unreachable=stops_with_unreachable_demand(best["lines"], demand))
st.plotly_chart(fig_best, width="stretch", key="primary_best_plot")

pdf_bytes_best = generate_network_plan_pdf("Optimiertes Netz", best["lines"], ids, demand)
st.download_button(
    "📄 Liniennetzplan als PDF herunterladen", data=pdf_bytes_best,
    file_name="liniennetzplan_optimiert.pdf", mime="application/pdf", key="primary_pdf_download",
)

st.caption("Ermittelt mit der besseren von zwei eigenen Methoden für dieses Szenario. Details unten.")

st.markdown("---")

with st.expander("🔧 Wie wir das erreichen – vollständiger Methodenvergleich", expanded=False):
    tabs = st.tabs(["⭐ Sternnetz", "📈 Nachfrage-optimiert", "📊 Vergleich"])

    with tabs[0]:
        st.caption("Radiales Netz vom nachfragestärksten Knotenpunkt aus - einfach und nachvollziehbar, aber nicht an der tatsächlichen Nachfrage ausgerichtet.")
        summary_star = render_network_panel("star", "Sternnetz", lines_star, coords, ids, demand, hub_idxs)

    with tabs[1]:
        st.caption("Baut Linien entlang der stärksten Nachfrage-Korridore, mit erzwungener Netzanbindung und Abdeckungs-Bonus (siehe README für die Details, die dahin geführt haben).")
        summary_greedy = render_network_panel("greedy", "Nachfrage-optimiert", lines_greedy, coords, ids, demand, hub_idxs)

    with tabs[2]:
        st.markdown("### Methodenvergleich")
        comp_rows = []
        for c in [summary_star, summary_greedy]:
            comp_rows.append({
                "Methode": c["label"],
                "Ohne Umstieg": f"{c['direct_pct']:.1f}%",
                "Mit 1 Umstieg": f"{c['one_transfer_pct']:.1f}%",
                "Nicht erreichbar": f"{c['unreachable_pct']:.1f}%",
                "Gesamtnachfrage": f"{c['total_demand']:.0f}",
            })
        st.dataframe(pd.DataFrame(comp_rows), width="stretch", hide_index=True)
        st.caption(
            "Beide Methoden werden mit derselben Bewertungsfunktion gegen dieselbe Nachfragematrix "
            "verglichen - fair vergleichbar, auch wenn die Konstruktionsstrategien sehr unterschiedlich sind."
        )

with st.expander("Wie funktioniert diese Demo?"):
    st.markdown(
        """
**Nachfragematrix:** Zwischen jedem Haltestellenpaar wird eine (symmetrische) Fahrgast-
Nachfrage generiert. Über den Regler "Pendler-Konzentration" lässt sich einstellen, wie
stark sich die Nachfrage auf wenige zentrale Hub-Haltestellen konzentriert (Pendlermuster)
statt gleichmäßig verteilt zu sein.

**Sternnetz:** Die nachfragestärkste Haltestelle wird zum Hub erklärt, die übrigen
Haltestellen per Polarwinkel um den Hub in Sektoren geteilt (dasselbe Prinzip wie beim
Sweep-Verfahren der Tourenplanung-Demo) - je Sektor eine vom Hub nach außen führende Linie.

**Nachfrage-optimierte Liniengenerierung:** Jede neue Linie startet am stärksten noch
nicht direkt bedienten Haltestellenpaar und wird an beiden Enden um die Haltestelle mit
dem größten zusätzlichen Nachfragebeitrag erweitert. Zwei zusätzliche Regeln waren nötig,
um brauchbare Ergebnisse zu erzielen (siehe README für die volle Geschichte): Ab der
zweiten Linie muss eine Anbindung an das bestehende Netz bestehen (sonst entstehen
unverbundene Teilnetze), und ein Wachstumsbonus verhindert, dass sich die Konstruktion
immer wieder auf dieselben wenigen Haltestellen konzentriert.

**Servicequalität statt Kosten:** Anders als bei der Tourenplanung-Demo (€/h/CO₂) zählt
hier vor allem eine andere Kennzahl: der Anteil der Fahrgastnachfrage, der ohne Umstieg
bzw. mit höchstens einem Umstieg erreichbar ist. Das ist die für einen Nahverkehrsbetrieb
tatsächlich relevante Größe - Busse fahren ohnehin nach Fahrplan, die "Ersparnis" liegt in
Fahrgastzufriedenheit und Auslastung, nicht in direkten Kosten.

**In echten Projekten** kämen meist weitere Nebenbedingungen dazu (Taktfrequenzen,
Umstiegszeiten, Fahrzeugkapazität, mehrstufige Umstiege, tatsächliches Straßennetz statt
Luftlinie) - das Grundprinzip aus Konstruktion und Bewertung bleibt aber dasselbe.
"""
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
    "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)"
)
