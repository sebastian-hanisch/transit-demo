# Liniennetz-Design für den öffentlichen Nahverkehr – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-transit-demo.streamlit.app/)**

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
| `transit_evaluation.py` | Umsteige-Bewertung (direkt / genau 1 Umstieg / nicht erreichbar) |
| `transit_visualization.py` | 2D-Netzkarte (Plotly) |
| `transit_exact.py` | exaktes Optimum auf kleinen Instanzen (vollständige Aufzählung, Exakt-Tab) |
| `transit_cpsat.py` | CP-SAT-Modell (OR-Tools) für größere Instanzen: zweistufig, mit Schranke |
| `transit_exact_results.py` | Laden der vorgerechneten Messreihen zum Exakt-Tab |
| `transit_pdf_export.py` | PDF-Liniennetzplan-Erzeugung |
| `transit_ui_panel.py` | Wiederverwendbares UI-Panel je Heuristik |
| `transit_presets.py` | Beispielszenarien, Permalink-Logik (`SETTING_SPECS`) |
| `tools/sweep_exact.py` | Messreihe: beide Heuristiken gegen das exakte Optimum (schreibt `data/exact_results.json`) |
| `tools/sweep_cpsat.py` | Messreihe: CP-SAT gegen Aufzählung, Modellverbesserungen, Skalierung (schreibt `data/cpsat_results.json`) |
| `data/exact_results.json`, `data/cpsat_results.json` | vorgerechnete Messreihen zum Exakt-Tab |

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
  genau einem Umstieg erreichbar ist (der Rest gilt als "nicht erreichbar", siehe
  Abschnitt "Definition von 'nicht erreichbar'") - die für einen Nahverkehrsbetrieb
  tatsächlich relevante Größe. Bewusst **keine** künstliche €-Umrechnung, da Busse ohnehin nach
  Fahrplan fahren und die "Ersparnis" in Fahrgastzufriedenheit liegt, nicht in direkten
  Betriebskosten.
- **Primäransicht "Ihr optimiertes Liniennetz"** von Anfang an (nicht erst
  nachträglich wie bei der Tourenplanung-Demo): zeigt die bessere der beiden Methoden
  direkt, kein Algorithmus-Name in der Überschrift, Methode als kleine Caption
  genannt; die grüne Erfolgsmeldung nennt die tatsächlich beste
  Methode (je nach Szenario Sternnetz oder nachfrage-optimiert). Vollständiger Methodenvergleich liegt im Expander "Wie wir das erreichen".
- **Tab „Optimum (exakt und CP-SAT)“:** Auf Instanzen mit bis zu 10 Haltestellen wird das Optimum vollständig aufgezählt, auf Instanzen bis 20 Haltestellen und 4 Linien rechnet ein CP-SAT-Modell (OR-Tools) mit Zeitlimit und Schranke; beide stehen neben den Heuristiken (siehe „Exakt-Tab“ unten).
- **Animation:** Schritt-Regler + Auto-Play zeigt, wie sich die Servicequalität
  aufbaut, während Linie für Linie hinzukommt.
- **Drei Ein-Klick-Beispielszenarien:** Kompaktstadt, Pendlerstadt, Mehrere Zentren.
- **Permalink und PDF-Export:** wie bei den anderen Demos.
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

Bei dieser Konfiguration erreichen beide vollständige Abdeckung und 0 % nicht
erreichbar, aber die nachfrage-optimierte Methode liefert 18,5-22,9 Prozentpunkte mehr
direkte (umstiegsfreie) Erreichbarkeit (je Instanz nachgerechnet, nicht aus den
Spannen der Tabelle abgeleitet) - ein sauberer, verdienter Vorteil, kein Zufallsergebnis
(`test_demand_greedy_generally_beats_star_on_direct_connectivity`).

## Exakt-Tab: wie weit liegen die Heuristiken vom Optimum?

Die Bewertung (`evaluate_network`) hängt nur davon ab, *welche* Haltestellen eine Linie verbindet, nicht von ihrer Reihenfolge, und eine zusätzliche Haltestelle auf einer Linie verschlechtert keine Erreichbarkeit.
Auf kleinen Instanzen genügt es deshalb, alle Netze aus verschiedenen Linien mit jeweils der vollen Haltestellenzahl durchzuprobieren (`transit_exact.py`: Bitmasken, vektorisiert mit numpy; höchstens 3 Mio. Netze).
Zielgröße ist die Auswahlregel der Primäransicht (erst die kleinste nicht erreichbare Nachfrage, dann die größte Nachfrage ohne Umstieg); zusätzlich wird das Optimum der Nachfrage ohne Umstieg allein
ausgewiesen (obere Schranke für jede Heuristik). Der Tab rechnet eine Instanz auf Knopfdruck; daneben steht eine Messreihe über 100 Zufalls-Seeds je Konfiguration (`tools/sweep_exact.py`, Pendler-Konzentration 0,5, zwei Hubs).

| Instanz (Haltestellen, Linien, höchstens je Linie) | Optimum ohne Umstieg | Sternnetz | Nachfrage-optimiert |
|---|---|---|---|
| 8, 3, 5 (27 720 Netze) | 97,5 ± 0,0 % | 63,2 ± 0,4 % (Abstand 34,3 ± 0,4 Punkte) | 91,6 ± 0,1 % (Abstand 5,9 ± 0,1 Punkte) |
| 9, 2, 4 (7 875 Netze) | 59,8 ± 0,3 % | 47,9 ± 1,0 % (Abstand 11,9 ± 1,0 Punkte) | 58,9 ± 0,3 % (Abstand 0,8 ± 0,1 Punkte) |
| 10, 3, 5 (2 635 500 Netze, 4,26 ± 0,04 s je Instanz) | 84,3 ± 0,2 % | 59,8 ± 0,3 % (Abstand 24,5 ± 0,2 Punkte) | 82,0 ± 0,3 % (Abstand 2,3 ± 0,2 Punkte) |

- **Die nachfrage-optimierte Heuristik liegt nah am Optimum, das Sternnetz nicht:** Der Abstand der Nachfrage ohne Umstieg zur oberen Schranke beträgt 0,8 bis 5,9 Prozentpunkte gegenüber 11,9 bis 34,3 beim Sternnetz; sie schlägt das Sternnetz in 100, 97 und 100 von 100 Instanzen. Keine Heuristik wird je vom Optimum nach der Auswahlregel geschlagen (jeweils 100 von 100).
- **Das Optimum nach der Auswahlregel trifft sie fast nie** (0, 4 und 0 von 100 Instanzen): Der Abstand ist klein, aber er bleibt. Bei 9 Haltestellen, 2 Linien und höchstens 4 Haltestellen je Linie lässt auch das Optimum 24,5 ± 0,2 % der Nachfrage unerreichbar (zwei Linien mit je 4 Haltestellen können nicht alle 9 Haltestellenpaare mit höchstens einem Umstieg verbinden); dort liegt die Heuristik sogar über dem Optimum der Auswahlregel in der direkten Nachfrage, weil die Regel zuerst die unerreichbare Nachfrage minimiert.
- **Grenzen:** Das Optimum gilt nur für die vereinfachte Aufgabe dieser Demo (keine Fahrzeiten, Takte oder Umstiegszeiten) und nur für kleine Instanzen; die Aussage „nahe am Optimum“ ist keine Aussage über die 20-Haltestellen-Szenarien der Hauptansicht. Das Sternnetz ist zudem eine bewusst einfache Baseline.
- **Verifikation (`tests/test_exact.py`):** Das Optimum stimmt mit einer unabhängigen Vollaufzählung über *alle* Haltestellenmengen (auch kürzere Linien) und der Bewertungsfunktion der App überein; keine Heuristik schlägt es; die interne Bewertung entspricht `evaluate_network`; die Messreihe ist in `tests/test_exact_results.py` nachgerechnet.

### CP-SAT für größere Instanzen (OR-Tools)

Die Aufzählung endet bei etwa 10 Haltestellen. Für größere Instanzen gibt es `transit_cpsat.py`: ein CP-SAT-Modell mit einer Ja/Nein-Entscheidung je Linie und Haltestelle, in **zwei Stufen** (erst die erreichbare Nachfrage, dann bei festgehaltener erreichbarer Nachfrage
die direkte). Findet es das Optimum im Zeitlimit, ist es bewiesen; sonst steht die beste gefundene Lösung mit einer **Schranke** da, und der Abstand zur Schranke begrenzt den Abstand zum Optimum in Prozentpunkten der direkten Nachfrage.
Die Aufzählung bleibt als unabhängiges Orakel: Jede Modellvariante muss auf kleinen Instanzen denselben Optimalwert finden (`tests/test_cpsat.py`).

- **Übereinstimmung:** Auf 60 kleinen Instanzen (7 bis 10 Haltestellen, 2 bis 3 Linien) beweist CP-SAT das Optimum in 60 von 60 Fällen und findet in 60 von 60 dasselbe Optimum wie die Aufzählung (Mittel 0,21 ± 0,04 s gegen 0,50 ± 0,13 s je Instanz).
- **Modellverbesserungen:** Das einfache Grundmodell beweist von 8 Instanzen mit 10 bis 12 Haltestellen und 3 Linien 7 in 136 s (Zeitlimit 30 s, je ein Lauf); mit allen Verbesserungen beweist es 8 in 23 s, der Median sinkt von 16,3 s auf 1,0 s. Die Wirkung steckt in drei Bausteinen: lex_symmetry (strenge Ordnung der austauschbaren Linien), line_cuts (je Linie höchstens m − 1 Paare je Haltestelle und m (m − 1) / 2 Paare, verschärft die lineare Relaxation) und compact_reach (je Linie und Haltestelle eine Variable statt je Paar und Linienpaar); ohne einen von ihnen steigt die Summe auf 47, 47 bzw. 40 s. exact_size, hint (Startlösung der Heuristik) und two_stage zeigen in dieser Reihe keinen messbaren Zeitgewinn (Summe 16, 19 bzw. 29 s); two_stage macht die Schranke in Prozentpunkten lesbar.
- **In Vorversuchen ohne messbare Wirkung und deshalb nicht im Code:** eine Obergrenze je Linie aus der besten m-Menge, Mindestabdeckung je Haltestelle in der zweiten Stufe und die Solver-Parameter `linearization_level`, `symmetry_level` und `cp_model_probing_level`.

Skalierung (10 Zufalls-Seeds je Zeile, Zeitlimit 30 s, 8 Arbeiter; Mittel ± Standardfehler; „Punkte“ = Prozentpunkte der direkten Nachfrage):

| Instanz (Haltestellen, Linien, Länge) | bewiesen | Sekunden | Lücke zur Schranke | CP-SAT ohne Umstieg | nachfrage-optimiert | CP-SAT besser um (Punkte) | Heuristik höchstens unter dem Optimum (Punkte) |
|---|---|---|---|---|---|---|---|
| 10, 3, 5 | 10 von 10 | 1,0 ± 0,1 | 0,0 ± 0,0 | 83,9 ± 0,5 % | 81,2 ± 1,2 % | 2,7 ± 0,9 | 2,7 ± 0,9 |
| 12, 3, 6 | 10 von 10 | 16,1 ± 1,8 | 0,0 ± 0,0 | 83,3 ± 0,2 % | 80,2 ± 0,4 % | 3,1 ± 0,3 | 3,1 ± 0,3 |
| 12, 4, 5 | 0 von 10 | 30,0 ± 0,0 | 4,0 ± 0,2 | 79,9 ± 0,3 % | 76,0 ± 0,5 % | 3,9 ± 0,3 | 7,9 ± 0,3 |
| 14, 4, 6 | 0 von 10 | 30,0 ± 0,0 | 4,2 ± 0,2 | 83,0 ± 0,4 % | 76,7 ± 0,4 % | 6,2 ± 0,3 | 10,4 ± 0,2 |
| 16, 4, 6 | 0 von 10 | 30,1 ± 0,0 | 5,1 ± 0,1 | 72,5 ± 0,4 % | 70,4 ± 0,5 % | 2,1 ± 0,2 | 7,2 ± 0,2 |
| 20, 4, 7 | 0 von 10 | 30,1 ± 0,0 | 4,7 ± 0,1 | 67,2 ± 0,3 % | 64,8 ± 0,4 % | 2,4 ± 0,2 | 7,1 ± 0,2 |

Mit 3 Linien beweist CP-SAT bis 12 Haltestellen; mit 4 Linien und ab 12 Haltestellen 0 von 10 Beweisen im Zeitlimit, die Lücke bleibt bei 4,0 bis 5,1 Punkten. CP-SAT findet dort trotzdem Netze, die 2,1 bis 6,2 Punkte besser sind als die Heuristik, und eine Schranke dafür, wie weit diese höchstens vom Optimum entfernt ist. Bei 20 Haltestellen und 4 Linien (Größe der Hauptansicht) liegt die Heuristik demnach höchstens 7,1 ± 0,2 Punkte unter dem Optimum.
Die Zeiten stammen von einem Entwicklungsrechner und schwanken zwischen Läufen; auf Streamlit Cloud (wenige Kerne) dauert es länger, das Zeitlimit gilt für die gesamte Rechnung.

Wirkung der Modellverbesserungen auf 8 Instanzen (Zeitlimit 30 s):

| Modell | bewiesen | Summe der Sekunden | Median |
|---|---|---|---|
| Grundmodell (alle Verbesserungen aus) | 7 von 8 | 136 s | 16,3 s |
| alle Verbesserungen | 8 von 8 | 23 s | 1,0 s |
| ohne exact_size | 8 von 8 | 16 s | 0,7 s |
| ohne lex_symmetry | 7 von 8 | 47 s | 2,1 s |
| ohne compact_reach | 8 von 8 | 40 s | 1,7 s |
| ohne hint | 8 von 8 | 19 s | 0,8 s |
| ohne two_stage | 8 von 8 | 29 s | 1,2 s |
| ohne line_cuts | 7 von 8 | 47 s | 1,7 s |

## Umsteige-Bewertungslogik: die neue, risikoreichste Komponente

Anders als bei den ersten beiden Demos gab es hier keine Vorlage aus einem bereits
gebauten System - die Logik "ist ein Haltestellenpaar direkt, mit einem Umstieg oder
gar nicht erreichbar" wurde komplett neu entwickelt und deshalb besonders sorgfältig
gegen handkonstruierte Fälle mit bekanntem korrektem Ergebnis geprüft (nicht nur
strukturell validiert): mehrere Linien mit gemeinsamer Haltestelle, ein
Mehrfach-Umsteigeknoten (eine Haltestelle auf drei Linien gleichzeitig), leere
Linienliste, keine Nachfrage. Alle Fälle in `test_evaluate_network_*` festgeschrieben.

## Definition von "nicht erreichbar" und Auswahlregel der Primäransicht

**"Nicht erreichbar" heißt "weder direkt noch mit genau einem Umstieg".** Die Kennzahl
`unreachable_pct` zählt auch Haltestellenpaare, die in einem zusammenhängenden Netz nur mit
zwei oder mehr Umstiegen verbunden wären (Linie A - B - C hintereinander, Halt auf A nach
Halt auf C). Die Oberfläche trägt das jetzt im Label ("Nicht erreichbar (>1 Umstieg nötig)",
wie schon im PDF-Export); `test_pairs_needing_two_transfers_count_as_not_reachable_despite_connected_network`
hält es fest. Wie relevant das ist, zeigt eine Stichprobe über 300 zufällige Konfigurationen
(6-40 Haltestellen, 2-8 Linien, Länge 3-12): beim Sternnetz nie (alle Linien teilen den
Hub, jedes Paar braucht höchstens einen Umstieg), beim nachfrage-optimierten Netz in 49 von
300 Fällen, im Extremfall mit 52 % der Nachfrage. Die Kennzahl "Mit 1 Umstieg erreichbar" ist
dabei exklusiv (genau ein Umstieg, ohne die direkten Verbindungen); "höchstens einer" wäre
direkt plus genau einer.

**Welches Netz die Primäransicht zeigt:** das mit der geringsten nicht erreichbaren
Nachfrage, bei Gleichstand das mit dem höchsten Anteil direkter Verbindungen. Das kann das
Sternnetz sein, obwohl die nachfrage-optimierte Methode mehr direkte Verbindungen schafft -
etwa im Beispiel "Mehrere Zentren" (30 Haltestellen, 6 Linien, Länge 7, 3 Hubs, Seed 8): das
nachfrage-optimierte Netz lässt 3 von 30 Haltestellen aus (27 abgedeckt, ein
zusammenhängendes Netz), 13,0 % der Nachfrage sind nicht erreichbar, dafür 57,5 % direkt; das
Sternnetz deckt alles ab (0 % nicht erreichbar), hat aber nur 34,5 % direkte Verbindungen und
wird deshalb als "optimiert" gezeigt. Die "0 % unerreichbar"-Aussage der Ergebnistabelle oben
gilt nur für die dort genannte Benchmark-Konfiguration (20 Haltestellen, 4 Linien, Länge 7).

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
- Kein bewiesenes Optimum für die Szenarien der Hauptansicht (20 Haltestellen, 4 Linien): Die Aufzählung ist dort unmöglich, CP-SAT beweist im Zeitlimit nichts, liefert aber bessere Netze und eine Schranke (siehe Exakt-Tab)
- Kein Mandl-Benchmark: Dessen Zielgröße (mittlere Reisezeit auf einem Straßennetz) hat diese Demo nicht, die Ergebnisse wären mit der Literatur nicht vergleichbar
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

133 Tests, laufen automatisch bei jedem Push/PR über GitHub Actions.

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
---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zum Thema: [ÖPNV und Fernverkehr optimieren](https://sebastianhanisch.net/oepnv-fernverkehr-optimierung.html).
