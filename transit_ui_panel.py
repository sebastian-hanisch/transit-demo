"""
Wiederverwendbares Streamlit-UI-Panel für eine einzelne Liniennetz-Heuristik:
Schritt-Regler (Linien werden nacheinander aufgebaut) + Auto-Play, Metriken,
Karte, PDF-Export.
"""

import time

import streamlit as st

from transit_evaluation import evaluate_network, stops_with_unreachable_demand
from transit_pdf_export import generate_network_plan_pdf
from transit_visualization import build_network_figure


def render_network_panel(prefix, label, lines, coords, ids, demand, hub_idxs):
    n_lines_built = sum(1 for l in lines if l)

    if n_lines_built > 1:
        auto_play = st.checkbox("▶️ Automatisch abspielen", key=f"{prefix}_auto")
        step = st.slider(
            f"Anzahl gebauter Linien ({label})", 1, n_lines_built, n_lines_built, key=f"{prefix}_step",
            help="Zeigt, wie sich die Servicequalität aufbaut, während Linie für Linie hinzukommt.",
        )
    else:
        auto_play = False
        step = n_lines_built
        if n_lines_built == 0:
            st.info("Bei dieser Konfiguration konnte keine sinnvolle Linie gebildet werden.")

    subset_lines = lines[:step]
    stats_step = evaluate_network(subset_lines, demand)

    m1, m2, m3 = st.columns(3)
    m1.metric("Ohne Umstieg erreichbar", f"{stats_step['direct_pct']:.1f}%")
    m2.metric("Mit 1 Umstieg erreichbar", f"{stats_step['one_transfer_pct']:.1f}%")
    m3.metric("Nicht erreichbar", f"{stats_step['unreachable_pct']:.1f}%")

    fig = build_network_figure(coords, subset_lines, hub_idxs, highlight_unreachable=stops_with_unreachable_demand(subset_lines, demand))
    plot_slot = st.empty()
    plot_slot.plotly_chart(fig, width="stretch", key=f"{prefix}_plot_{step}")
    st.caption("🔴 Rot markierte Haltestellen haben mindestens eine Nachfragebeziehung, die weder direkt noch mit einem Umstieg erreichbar ist. Grau = noch auf keiner Linie.")

    if auto_play:
        for s in range(1, n_lines_built + 1):
            f = build_network_figure(coords, lines[:s], hub_idxs, highlight_unreachable=stops_with_unreachable_demand(lines[:s], demand))
            plot_slot.plotly_chart(f, width="stretch", key=f"{prefix}_auto_{s}")
            time.sleep(0.3)

    pdf_bytes = generate_network_plan_pdf(label, lines, ids, demand)
    st.download_button(
        "📄 Liniennetzplan als PDF herunterladen", data=pdf_bytes,
        file_name=f"liniennetz_{prefix}.pdf", mime="application/pdf", key=f"{prefix}_pdf_download",
    )

    final_stats = evaluate_network(lines, demand)
    return {"label": label, "lines": lines, **final_stats}
