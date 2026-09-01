"""
2D-Kartendarstellung des Liniennetzes mit Plotly: Haltestellen als Punkte
(unbediente grau markiert), Linien als farbige Pfade zwischen aufeinander-
folgenden Haltestellen, Nachfrage-Hubs als Sterne hervorgehoben.
"""

import plotly.graph_objects as go

from transit_constants import LINE_COLORS


def build_network_figure(coords, lines, hub_idxs=None, highlight_unreachable=None):
    """Baut die Netzkarte für einen gegebenen Stand (Teilmenge der Linien -
    wird auch für die Schritt-für-Schritt-Animation verwendet, bei der
    Linien nacheinander erscheinen)."""
    fig = go.Figure()

    covered = set()
    for line in lines:
        covered.update(line)
    n_stops = len(coords)
    unreachable_set = set(highlight_unreachable) if highlight_unreachable else set()

    marker_colors = []
    for i in range(n_stops):
        if i in unreachable_set:
            marker_colors.append("#ef4444")
        elif i in covered:
            marker_colors.append("#374151")
        else:
            marker_colors.append("lightgray")

    fig.add_trace(
        go.Scatter(
            x=coords[:, 0], y=coords[:, 1], mode="markers+text",
            marker=dict(size=10, color=marker_colors, line=dict(width=1, color="white")),
            text=[str(i + 1) for i in range(n_stops)], textposition="top center",
            name="Haltestellen", hoverinfo="text", showlegend=False,
        )
    )

    for idx, line in enumerate(lines):
        if len(line) < 2:
            continue
        color = LINE_COLORS[idx % len(LINE_COLORS)]
        xs = [coords[s][0] for s in line]
        ys = [coords[s][1] for s in line]
        fig.add_trace(
            go.Scatter(
                x=xs, y=ys, mode="lines", line=dict(color=color, width=3),
                name=f"Linie {idx + 1}", hoverinfo="skip",
            )
        )

    if hub_idxs is not None and len(hub_idxs) > 0:
        fig.add_trace(
            go.Scatter(
                x=[coords[h][0] for h in hub_idxs], y=[coords[h][1] for h in hub_idxs],
                mode="markers", marker=dict(size=16, symbol="star", color="black", line=dict(width=1, color="white")),
                name="Nachfrage-Hub", hoverinfo="text", text=["Nachfrage-Hub"] * len(hub_idxs),
            )
        )

    fig.update_layout(
        xaxis=dict(range=[-5, 105], title="x", zeroline=False),
        yaxis=dict(range=[-5, 105], title="y", zeroline=False, scaleanchor="x"),
        height=520, margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    # fixedrange auf beiden Achsen: verhindert Pinch-Zoom/Drag-Pan im Chart,
    # damit auf Touch-Geräten stattdessen die Seite normal gescrollt wird
    # (Hover-Tooltips bleiben davon unberührt).
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig
