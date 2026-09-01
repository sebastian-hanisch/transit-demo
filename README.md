# 🚌 Liniennetz-Design (ÖPNV)

Interaktive Demo zur Gestaltung eines Buslinien-Netzes anhand einer Fahrgast-Nachfragematrix.

**[→ Demo live ausprobieren](https://sebastianhanisch-transit-demo.streamlit.app/)**

## Worum geht's?

Ausgehend von Haltestellen und Nachfragedaten: welches Liniennetz bringt möglichst viele Fahrgäste ohne Umsteigen ans Ziel? Anders als bei kosten-getriebener Tourenplanung zählt hier vor allem eine Kennzahl: der Anteil der Nachfrage, der ohne Umstieg erreichbar ist.

## Methodik

- Zwei selbst implementierte Ansätze im Vergleich: ein **Sternnetz** (radial vom nachfragestärksten Knotenpunkt, wie viele historisch gewachsene Netze) und eine **nachfrage-optimierte Liniengenerierung** (folgt den stärksten Nachfrage-Korridoren)
- Schritt-für-Schritt-Animation, Permalink für eigene Beispielszenarien

Als eigenständiges Portfolio-Projekt entstanden — zeigt dieselbe Methodik (Konstruktionsheuristik + Bewertung + Vergleich) wie die anderen Demos, angewendet auf ein neues Feld außerhalb der Fracht-/Logistik-Kernspezialisierung.

## Lokal ausführen

```bash
pip install -r requirements-dev.txt
streamlit run app.py
```

Tests: `pytest tests/ -v`

---

Teil des [Operations-Research-Demo-Portfolios](https://sebastianhanisch.net/demos.html) von [Sebastian Hanisch](https://sebastianhanisch.net) — Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html).
