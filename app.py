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
import transit_exact as exact
import transit_exact_results as exact_results
from transit_evaluation import METHOD_PHRASES, evaluate_network, stops_with_unreachable_demand
from transit_heuristics import demand_greedy_construction, star_network_construction
from transit_pdf_export import generate_network_plan_pdf
from transit_presets import apply_preset, bounds, init_session_state_defaults, load_permalink_settings, randomize_seed, sync_query_params
from transit_ui_panel import render_network_panel
from transit_visualization import build_network_figure

st.set_page_config(page_title="Liniennetz-Design – Sebastian Hanisch", layout="wide")


def _de(x, digits=1):
    """Zahl mit Dezimalkomma (nur die Zahl, nie ein ganzer Satz)."""
    return f"{x:.{digits}f}".replace(".", ",")


def _de_int(x):
    """Ganzzahl mit Punkt als Tausendertrenner (nur die Zahl, nie ein ganzer Satz)."""
    return f"{x:,}".replace(",", ".")


@st.cache_data(show_spinner=False, max_entries=8)
def _exact_instance(n, k, length, seed, hub_conc, n_hubs):
    """Kleine Instanz mit beiden Heuristiken und dem exakten Optimum (vollständige Aufzählung); zwischengespeichert je Einstellung."""
    coords_e, demand_e, hubs_e = generate_stops_and_demand(n, seed, hub_concentration=hub_conc, n_hubs=n_hubs)
    result = exact.solve_exact(coords_e, demand_e, k, length)
    star = star_network_construction(coords_e, demand_e, k, length)
    greedy = demand_greedy_construction(coords_e, demand_e, k, length)
    return coords_e, demand_e, hubs_e, result, star, greedy, evaluate_network(star, demand_e), evaluate_network(greedy, demand_e)

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
m2.metric(
    "Mit 1 Umstieg erreichbar", f"{best['one_transfer_pct']:.1f}%",
    help="Genau ein Umstieg nötig (ohne die direkten Verbindungen links).",
)
m3.metric(
    "Nicht erreichbar (>1 Umstieg nötig)", f"{best['unreachable_pct']:.1f}%",
    delta=f"{unreachable_diff:+.1f} Pp. ggü. Alternative", delta_color="inverse",
    help="Haltestellenpaare, die weder direkt noch mit genau einem Umstieg verbunden sind. Dazu zählen "
         "Haltestellen, die auf keiner Linie liegen, und Paare, die erst mit zwei oder mehr Umstiegen erreichbar wären.",
)

if direct_gain > 1.0:
    # Die Meldung nennt die tatsächlich beste Methode (nicht immer die nachfrage-optimierte).
    st.success(
        f"💡 Mit {METHOD_PHRASES[best['key']]} erreichen **{best['direct_pct']:.1f}%** Ihrer "
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

st.caption(
    "Ermittelt mit der besseren von zwei eigenen Methoden für dieses Szenario (zuerst wenigste nicht "
    "erreichbare Nachfrage, dann meiste direkte Verbindungen). Details unten."
)

st.markdown("---")

with st.expander("🔧 Wie wir das erreichen – vollständiger Methodenvergleich", expanded=False):
    tabs = st.tabs(["⭐ Sternnetz", "📈 Nachfrage-optimiert", "📊 Vergleich", "🎯 Exakt (kleine Instanz)"])

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
                "Nicht erreichbar (>1 Umstieg nötig)": f"{c['unreachable_pct']:.1f}%",
                "Gesamtnachfrage": f"{c['total_demand']:.0f}",
            })
        st.dataframe(pd.DataFrame(comp_rows), width="stretch", hide_index=True)
        st.caption(
            "Beide Methoden werden mit derselben Bewertungsfunktion gegen dieselbe Nachfragematrix "
            "verglichen - fair vergleichbar, auch wenn die Konstruktionsstrategien sehr unterschiedlich sind."
        )

    with tabs[3]:
        st.markdown(
            """
**Wie weit sind die beiden Heuristiken vom Optimum entfernt?** Auf **kleinen** Instanzen lässt sich das Optimum **vollständig aufzählen**. Zwei Beobachtungen machen das möglich:
Die Bewertung hängt nur davon ab, *welche* Haltestellen eine Linie verbindet, nicht von ihrer Reihenfolge, und eine zusätzliche Haltestelle auf einer Linie verschlechtert keine Erreichbarkeit.
Es genügt also, alle Netze aus verschiedenen Linien mit jeweils der **vollen** Haltestellenzahl auszuprobieren. Bewertet wird nach der Regel der Primäransicht: erst die kleinste nicht erreichbare Nachfrage,
dann die größte Nachfrage ohne Umstieg. Zusätzlich steht das Optimum der Nachfrage ohne Umstieg allein da (obere Schranke für jede Heuristik).

Haltestellenmuster und Nachfrage kommen aus den Reglern der Seitenleiste (Zufalls-Seed, Pendler-Konzentration, Hubs); Anzahl der Haltestellen, Linien und Linienlänge stellen Sie hier getrennt ein, weil große Netze nicht aufzählbar sind.
"""
        )
        ex1, ex2, ex3 = st.columns(3)
        ex_n = ex1.slider("Haltestellen (kleine Instanz)", 6, 10, 8, key="exact_n")
        ex_k = ex2.slider("Linien", 2, 3, 3, key="exact_k")
        ex_len = ex3.slider("Max. Haltestellen je Linie", 3, 6, 5, key="exact_len")
        ex_combos = exact.n_combinations(ex_n, ex_k, ex_len)
        biggest = next((c for c in exact_results.configs() if (c["n"], c["k"], c["L"]) == (10, 3, 5)), None)
        st.caption(
            f"Aufzuzählen: {_de_int(exact.n_candidates(ex_n, ex_len))} Kandidaten-Linien, daraus {_de_int(ex_combos)} Netze"
            + (f" (das größte Beispiel mit 10 Haltestellen, 3 Linien und 5 Haltestellen je Linie dauerte bei der Messreihe {exact_results.stat_text(biggest['solve_seconds'], 1)} s je Instanz auf dem Entwicklungsrechner; auf dem Server kann es länger dauern)." if biggest else ".")
        )
        ex_key = (ex_n, ex_k, ex_len, int(seed), float(hub_concentration), int(n_hubs))
        if st.button("Optimum berechnen (alle Netze aufzählen)", key="exact_start"):
            st.session_state["exact_done"] = ex_key
        if st.session_state.get("exact_done") == ex_key:
            with st.spinner(f"Zähle {_de_int(ex_combos)} Netze auf …"):
                e_coords, e_demand, e_hubs, e_res, e_star, e_greedy, e_stats_star, e_stats_greedy = _exact_instance(*ex_key)
            upper = e_res.stats_direct["direct_pct"]
            rows_e = []
            for label, stats_e in (("Sternnetz", e_stats_star), ("Nachfrage-optimiert", e_stats_greedy), ("Optimum (Auswahlregel der App)", e_res.stats_lex),
                                   ("Obere Schranke: Optimum der Nachfrage ohne Umstieg", e_res.stats_direct)):
                rows_e.append({"Netz": label, "Ohne Umstieg": f"{_de(stats_e['direct_pct'], 1)}%", "Mit 1 Umstieg": f"{_de(stats_e['one_transfer_pct'], 1)}%",
                               "Nicht erreichbar": f"{_de(stats_e['unreachable_pct'], 1)}%", "Abstand zur oberen Schranke (Prozentpunkte)": _de(upper - stats_e['direct_pct'], 1)})
            st.dataframe(pd.DataFrame(rows_e), width="stretch", hide_index=True)
            gap_g, gap_s = upper - e_stats_greedy["direct_pct"], upper - e_stats_star["direct_pct"]
            st.markdown(
                f"Bei {ex_n} Haltestellen, {ex_k} Linien und höchstens {ex_len} Haltestellen je Linie liegt die nachfrage-optimierte Heuristik {_de(gap_g, 1)} Prozentpunkte unter der oberen Schranke der Nachfrage ohne Umstieg, "
                f"das Sternnetz {_de(gap_s, 1)}. Aufgezählt wurden {_de_int(e_res.n_combinations)} Netze in {_de(e_res.seconds, 2)} s."
            )
            if e_res.stats_lex["unreachable_pct"] > 0:
                st.caption(f"Auch das Optimum lässt {_de(e_res.stats_lex['unreachable_pct'], 1)} % der Nachfrage unerreichbar: Bei dieser Zahl und Länge der Linien kann es nicht alle Haltestellenpaare mit höchstens einem Umstieg verbinden.")
            mc1, mc2 = st.columns(2)
            with mc1:
                st.markdown("**Nachfrage-optimiert**")
                st.plotly_chart(build_network_figure(e_coords, e_greedy, e_hubs, stops_with_unreachable_demand(e_greedy, e_demand)), width="stretch", key="exact_map_greedy")
            with mc2:
                st.markdown("**Optimum**")
                st.plotly_chart(build_network_figure(e_coords, e_res.lines_lex, e_hubs, stops_with_unreachable_demand(e_res.lines_lex, e_demand)), width="stretch", key="exact_map_opt")
            st.caption("Die Reihenfolge der Haltestellen im Optimum ist nur für die Karte gewählt (Nächster-Nachbar-Weg); die Bewertung ignoriert sie. Bei Gleichstand gewinnt die Aufzählung mit den kleinsten Haltestellen-Indizes.")

        st.markdown("**Vorgerechnet über 100 Zufalls-Seeds je Konfiguration** (Pendler-Konzentration 0,5, zwei Hubs; Mittel ± Standardfehler; Optimum jeweils vollständig aufgezählt):")
        rows_r = []
        for c in exact_results.configs():
            for key_m, label_m in (("star", "Sternnetz"), ("greedy", "Nachfrage-optimiert")):
                m = c[key_m]
                rows_r.append({"Instanz": f"{c['n']} Haltestellen, {c['k']} Linien, höchstens {c['L']} je Linie", "Methode": label_m, "Ohne Umstieg (%)": exact_results.stat_text(m["direct"]),
                               "Optimum ohne Umstieg (%)": exact_results.stat_text(c["exakt"]["direct_obere_schranke"]), "Abstand zur oberen Schranke (Punkte)": exact_results.stat_text(m["luecke_direkt_zur_oberen_schranke"]),
                               "Nicht erreichbar (%)": exact_results.stat_text(m["unreachable"]), "Optimum nach Auswahlregel getroffen": exact_results.share_text(m["optimum_getroffen"])})
        st.dataframe(pd.DataFrame(rows_r), width="stretch", hide_index=True)
        st.caption("Das Optimum ist nur die Obergrenze für die Qualität einer Heuristik auf dieser vereinfachten Aufgabe (keine Fahrzeiten, keine Takte, keine Umstiegszeiten) und nur für kleine Instanzen berechenbar.")

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
bzw. mit genau einem Umstieg erreichbar ist (alles Übrige gilt als "nicht erreichbar": Paare,
die zwei oder mehr Umstiege bräuchten, und Haltestellen, die auf keiner Linie liegen). Das
ist die für einen Nahverkehrsbetrieb tatsächlich relevante Größe - Busse fahren ohnehin nach
Fahrplan, die "Ersparnis" liegt in Fahrgastzufriedenheit und Auslastung, nicht in direkten
Kosten.

**Welches Netz zuerst gezeigt wird:** Die Primäransicht nimmt das Netz mit der geringsten
nicht erreichbaren Nachfrage, bei Gleichstand das mit dem höchsten Anteil direkter
Verbindungen. Das kann das Sternnetz sein, obwohl die nachfrage-optimierte Methode mehr
direkte Verbindungen schafft: lässt sie Haltestellen aus (z. B. im Beispiel "Mehrere Zentren"
liegen 3 von 30 Haltestellen auf keiner Linie, 13,0 % der Nachfrage sind nicht erreichbar),
gewinnt das lückenlose Sternnetz (34,5 % statt 57,5 % direkte Verbindungen). Beide Netze mit
allen Kennzahlen stehen im Vergleichs-Tab.

**In echten Projekten** kämen meist weitere Nebenbedingungen dazu (Taktfrequenzen,
Umstiegszeiten, Fahrzeugkapazität, mehrstufige Umstiege, tatsächliches Straßennetz statt
Luftlinie) - das Grundprinzip aus Konstruktion und Bewertung bleibt aber dasselbe.
"""
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zum Thema: [ÖPNV und Fernverkehr optimieren](https://sebastianhanisch.net/oepnv-fernverkehr-optimierung.html)."
)
