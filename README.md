# Liniennetz-Design für den öffentlichen Nahverkehr – Streamlit-Demo

Interaktive Demo zur Gestaltung eines Buslinien-Netzes anhand einer Fahrgast-
Nachfragematrix. Dritte Demo im Portfolio für die Website "Sebastian Hanisch –
Operations Research und Machine Learning", nach Tourenplanung (VRP) und
3D-Packungsoptimierung.

## Einordnung: ein neues Feld, dieselbe Methodik

Die dokumentierten Kernspezialisierungen liegen im Fracht-/Logistikbereich
(Tourenplanung, Container-/Palettenpackung, Wechselbrücken-Hofmanagement), nicht
speziell im ÖPNV. Diese Demo zeigt dieselbe Methodik (Konstruktionsheuristik +
Bewertung + Vergleich) auf ein neues Feld angewendet - **methodische Vielseitigkeit**,
nicht jahrelange Nahverkehrs-Facherfahrung. Das sollte sich auch in der
Website-Formulierung widerspiegeln.

Das zugrunde liegende Problem (Transit Network Design Problem, TNDP) ist in der
Fachliteratur gut dokumentiert, aber deutlich anspruchsvoller als Tourenplanung oder
Bin-Packing: durchgehend als NP-schwer, nicht-konvex und mehrzielig beschrieben:
Standardansätze sind zweistufig (Routengenerierung + genetischer Algorithmus/Simulated
Annealing obendrauf). Diese Demo bildet ein bewusst vereinfachtes Teilproblem ab
(Liniennetz-Design bei fester Anzahl Linien, ohne Taktfrequenz/Fahrplan) - kein
Anspruch auf realistische Vollständigkeit, sondern auf ein nachvollziehbares,
korrekt verifiziertes Kernprinzip.

## Dateistruktur

Von Anfang an modular gebaut (Lehre aus den ersten beiden Demos):

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Hauptablauf (Primäransicht, Sidebar, Detail-Expander) |
| `transit_constants.py` | Konstanten |
| `transit_demand.py` | Haltestellen- und Nachfragematrix-Generierung |
| `transit_heuristics.py` | Sternnetz- und nachfrage-optimierte Liniengenerierung |
| `transit_evaluation.py` | Umsteige-Bewertung (direkt/1 Umstieg/unerreichbar) |
| `transit_visualization.py` | 2D-Netzkarte (Plotly) |
| `transit_pdf_export.py` | PDF-Liniennetzplan-Erzeugung |
| `transit_feedback.py` | Feedback-Logging |
| `transit_ui_panel.py` | Wiederverwendbares UI-Panel je Heuristik |
| `transit_presets.py` | Beispielszenarien, Permalink-Logik (`SETTING_SPECS`) |

## Funktionsumfang

- **Nachfragematrix statt fixer Stopp-Liste:** Zwischen jedem Haltestellenpaar wird
  eine symmetrische Fahrgastnachfrage generiert, konfigurierbar über eine
  "Pendler-Konzentration" (0 = gleichverteilt, 1 = stark auf wenige Hub-Haltestellen
  konzentriert - realistisches Pendlermuster).
- **Zwei eigene Heuristiken:**
  - *Sternnetz* (Baseline): nachfragestärkste Haltestelle wird zum Hub, restliche
    Haltestellen per Polarwinkel um den Hub in Sektoren geteilt (dasselbe Prinzip
    wie Sweep in der Tourenplanung-Demo), je Sektor eine radiale Linie.
  - *Nachfrage-optimierte Liniengenerierung*: baut Linien entlang der stärksten
    Nachfrage-Korridore, mit zwei nachträglich als notwendig erkannten Regeln (siehe
    unten).
- **Servicequalität statt Kosten als Kennzahl:** Anders als bei der Tourenplanung-Demo
  (€/h/CO₂) zählt hier der Anteil der Fahrgastnachfrage, der ohne Umstieg bzw. mit
  höchstens einem Umstieg erreichbar ist - die für einen Nahverkehrsbetrieb tatsächlich
  relevante Größe. Bewusst **keine** künstliche €-Umrechnung, da Busse ohnehin nach
  Fahrplan fahren und die "Ersparnis" in Fahrgastzufriedenheit liegt, nicht in direkten
  Betriebskosten.
- **Primäransicht "Ihr optimiertes Liniennetz"** von Anfang an (nicht erst
  nachträglich wie bei der Tourenplanung-Demo): zeigt die bessere der beiden Methoden
  direkt, kein Algorithmus-Name in der Überschrift, Methode als kleine Caption
  genannt. Vollständiger Methodenvergleich liegt im Expander "Wie wir das erreichen".
- **Animation:** Schritt-Regler + Auto-Play zeigt, wie sich die Servicequalität
  aufbaut, während Linie für Linie hinzukommt.
- **Drei Ein-Klick-Beispielszenarien:** Kompaktstadt, Pendlerstadt, Mehrere Zentren.
- **Permalink, Feedback-Mechanismus, PDF-Export:** wie bei den anderen Demos.
- **Von Anfang an mit dem `SETTING_SPECS`-Muster gebaut** (Wahrheitsquelle für
  Wertebereiche) und von Anfang an gegen NaN/Infinity/außerhalb-des-Bereichs-Werte im
  Permalink abgesichert - beides war bei der Tourenplanung-Demo erst nachträglich
  gefundene und behobene Bugs.

## Zwei Konstruktionsfehler beim Bauen gefunden - keine Kleinigkeiten

Die "nachfrage-optimierte" Heuristik funktionierte in ihrer ersten Version nicht wie
beabsichtigt. Beide Fehler wurden durch systematisches Benchmarking (nicht durch
Zufall) gefunden, bevor die Demo das erste Mal auslieferungsfertig war.

**1. Unverbundene Teilnetze.** Die ursprüngliche Version wählte für jede neue Linie
einfach das nächststärkste noch unbediente Haltestellenpaar - ohne Rücksicht darauf,
ob die neue Linie überhaupt an das bestehende Netz anschließt. Ergebnis: **53-61 %
der Nachfrage unerreichbar**, weil die Linien isolierte Inseln bildeten, während das
simple Sternnetz (garantiert verbunden, da alle Linien den Hub teilen) bei **0 %
unerreichbar** lag - der "schlauere" Ansatz war strukturell schlechter. Fix: Ab der
zweiten Linie muss das Startpaar mindestens eine bereits im Netz enthaltene
Haltestelle einschließen - genau wie ein reales Nahverkehrsnetz an Knotenpunkten
wächst (`test_demand_greedy_network_is_connected`).

**2. Nach dem ersten Fix: nur ein Bruchteil abgedeckt.** Mit der Netzanbindungs-Regel
allein blieb ein zweites Problem bestehen: Die Konstruktion konzentrierte sich immer
wieder auf dieselben wenigen nachfragestarken Haltestellen (11 von 20 in einem
Testfall), weil die Erweiterungslogik ausschließlich nach maximalem
Nachfragegewinn sucht - und ein bereits mehrfach genutzter Knotenpunkt bietet fast
immer den höchsten Gewinn, egal ob er schon abgedeckt ist. Fix: ein Wachstumsbonus
(`growth_bonus=2.5`) bevorzugt bei Start- und Erweiterungsentscheidungen noch nicht
abgedeckte Haltestellen (`test_demand_greedy_achieves_full_coverage`).

**Ergebnis nach beiden Fixes** (20 Haltestellen, 4 Linien, über 5 Testinstanzen):

| Methode | Ohne Umstieg | Abdeckung | Unerreichbar |
|---|---|---|---|
| Sternnetz | 44,9-48,1 % | 20/20 | 0,0 % |
| Nachfrage-optimiert | 66,6-68,9 % | 20/20 | 0,0 % |

Beide erreichen jetzt vollständige Abdeckung und 0 % unerreichbar, aber die
nachfrage-optimierte Methode liefert 18-24 Prozentpunkte mehr direkte (umstiegsfreie)
Erreichbarkeit - ein sauberer, verdienter Vorteil, kein Zufallsergebnis
(`test_demand_greedy_generally_beats_star_on_direct_connectivity`).

## Umsteige-Bewertungslogik: die neue, risikoreichste Komponente

Anders als bei den ersten beiden Demos gab es hier keine Vorlage aus einem bereits
gebauten System - die Logik "ist ein Haltestellenpaar direkt, mit einem Umstieg oder
gar nicht erreichbar" wurde komplett neu entwickelt und deshalb besonders sorgfältig
gegen handkonstruierte Fälle mit bekanntem korrektem Ergebnis geprüft (nicht nur
strukturell validiert): mehrere Linien mit gemeinsamer Haltestelle, ein
Mehrfach-Umsteigeknoten (eine Haltestelle auf drei Linien gleichzeitig), leere
Linienliste, keine Nachfrage. Alle Fälle in `test_evaluate_network_*` festgeschrieben.

## Ein Fund bei der gezielten Bug-Suche: halb-fertige Funktion

`build_network_figure` hatte von Anfang an einen `highlight_unreachable`-Parameter, der
in der Funktion auch korrekt genutzt wurde (Haltestellen mit unerreichbarer
Nachfrage rot markieren) - aber **kein einziger Aufrufer hat ihn je befüllt**. Die
Funktionalität war vollständig implementiert, aber komplett unsichtbar. Statt den toten
Code zu entfernen, wurde er fertiggestellt: eine neue Funktion
`stops_with_unreachable_demand` berechnet die betroffenen Haltestellen, jetzt in allen
drei Kartenaufrufen (Primäransicht, beide Detail-Tabs) verdrahtet, inklusive erklärender
Caption. Regressionstest: `test_stops_with_unreachable_demand_was_dead_code_now_wired_up`,
`test_unreachable_highlighting_wired_into_all_map_calls`.

Zusätzlich geprüft und für unauffällig befunden: identische Koordinaten zweier
Haltestellen (kein Fehler in der Winkelberechnung), Konsistenz der Prozentwerte
(direkt + 1 Umstieg + unerreichbar = 100 % über 29 Zufallsinstanzen verifiziert),
Erklärtexte gegen tatsächliches Codeverhalten.

## Bewusst nicht enthalten (Scope-Entscheidung)

- Keine Taktfrequenzen/Fahrpläne (reines Liniennetz-Design, keine Zeitkomponente)
- Kein echtes Straßennetz (Luftlinie zwischen Haltestellen, wie bei den ersten beiden
  Demos vor der Straßennetz-Erweiterung)
- Keine Fahrzeugkapazität oder Umlaufplanung
- Kein dritter/vierter Ansatz (metaheuristisch, z. B. genetischer Algorithmus) - zwei
  Methoden mit echtem Charakterunterschied reichen für die Kernaussage
- Haltestellen nicht editierbar (Nachfrage ist an die Generierung gekoppelt - Bearbeiten
  einzelner Positionen hätte eine Nachfrage-Neuberechnung erfordert, für den Scope
  dieser Demo nicht nötig)

## Vom Nutzer gemeldet: "Neues Szenario generieren" tat bei unverändertem Seed nichts

Im Zuge einer Konsistenzprüfung über alle vier Demos gefunden (identischer Fehler auch
in der Tourenplanung-Demo, dort zuerst gefunden und behoben - siehe dortiges README für
die volle Herleitung): der Button rief nur ein normales `st.button()` auf. Sein Wert
floss zwar in die `gen_key`-Neuberechnung ein (`regenerate or force_regen`), aber die
automatische Neugenerierung reagiert bereits auf jede Änderung von Parametern oder Seed
- blieb der Seed unverändert, lieferte die deterministische Zufallserzeugung dieselben
Werte erneut. Ein Klick löste zwar technisch eine Neuberechnung aus, das Ergebnis war
aber identisch - für den Nutzer sichtbar ein reiner Leerlauf-Klick.

**Der bestehende Test hatte diese Lücke nicht erkannt:** `test_regenerate_button` prüfte
nur "kein Absturz", nie die tatsächliche Wirkung. Auf echte Wirkungsprüfung umgestellt
(Seed muss sich nach dem Klick unterscheiden).

**Fix, kein ersatzloses Entfernen:** statt den wirkungslosen Button zu streichen, bekam
er eine echte Funktion - er würfelt jetzt einen neuen Zufalls-Seed (`randomize_seed()`
in `transit_presets.py`, nach demselben `on_click`-Callback-Muster wie `apply_preset`).
Ein Klick liefert garantiert ein komplett neues Szenario, ohne selbst eine neue
Seed-Zahl eintippen zu müssen.
`test_regenerate_button` (verstärkt).

## 1. Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## 2. Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

59 Tests, laufen automatisch bei jedem Push/PR über GitHub Actions.

## 3. Kostenlos online stellen (Streamlit Community Cloud)

1. Diesen Ordner in ein GitHub-Repository hochladen.
2. Auf [share.streamlit.io](https://share.streamlit.io) anmelden.
3. "New app" → Repository und `app.py` als Hauptdatei → Deploy.

## 4. Anpassungsideen für später

- Taktfrequenz-/Fahrplan-Optimierung (Umstiegszeiten synchronisieren) als eigenes,
  eigenständiges Teilproblem - mathematisch andersartig (periodisches
  Scheduling-Problem), eher eine vierte Demo als eine Erweiterung dieser
- Echtes Straßennetz statt Luftlinie
- Gewichtete Mehrfachziele (Fahrgastzeit vs. Betreiberkosten/Linienlänge) explizit
  gegeneinander abwägbar machen
- Test an einem echten Mobilgerät
