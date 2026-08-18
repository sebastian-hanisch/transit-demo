"""
Automatisierte Tests für die Liniennetz-Design-Demo.

Zwei Ebenen, wie bei den anderen Demos:
1. UI-Tests über streamlit.testing.v1.AppTest.
2. Unit-Tests der reinen Logik-Funktionen (normale Imports, da die Logik in
   eigenen Modulen ohne Streamlit-UI-Code liegt).

Ausführen mit: pytest tests/ -v
"""

import os
import sys

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

APP_DIR = os.path.join(os.path.dirname(__file__), "..")
APP_PATH = os.path.join(APP_DIR, "app.py")
TIMEOUT = 90

sys.path.insert(0, os.path.abspath(APP_DIR))


def fresh_app():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=TIMEOUT)
    return at


def assert_ok(at):
    assert not at.exception, f"Unerwartete Exception(s): {[e.message for e in at.exception]}"


# ==========================================================================
# 1. UI-Tests (AppTest)
# ==========================================================================

def test_default_load():
    at = fresh_app()
    assert_ok(at)


def test_primary_view_shows_three_service_metrics():
    at = fresh_app()
    assert_ok(at)
    labels = [m.label for m in at.metric[:3]]
    assert labels == ["Ohne Umstieg erreichbar", "Mit 1 Umstieg erreichbar", "Nicht erreichbar"]


def test_primary_view_no_algorithm_name_in_headline():
    at = fresh_app()
    assert_ok(at)
    headlines = [str(m.value) for m in at.markdown if "Ihr optimiertes Liniennetz" in str(m.value)]
    assert headlines
    for name in ["Sternnetz", "Nachfrage-optimiert"]:
        assert name not in headlines[0]


def test_primary_view_method_attribution_in_caption():
    at = fresh_app()
    assert_ok(at)
    captions = [str(c.value) for c in at.caption]
    assert any("zwei eigenen Methoden" in c for c in captions)


@pytest.mark.parametrize("label", ["Kompaktstadt", "Pendlerstadt", "Mehrere Zentren"])
def test_presets_apply_without_crash(label):
    at = fresh_app()
    btn = [b for b in at.button if label in b.label][0]
    btn.click().run(timeout=TIMEOUT)
    assert_ok(at)


def test_regenerate_button():
    """Verstärkt auf Nutzerhinweis: prüfte zuvor nur 'kein Absturz', nicht
    die tatsächliche Wirkung - genau die Art Test, die den ursprünglichen
    Fehler (Button ohne Effekt bei unverändertem Seed, siehe
    randomize_seed-Docstring in transit_presets.py) nicht erkannt hätte."""
    at = fresh_app()
    seed_before = at.sidebar.number_input(key="seed_input").value
    at.sidebar.button[0].click().run(timeout=TIMEOUT)
    assert_ok(at)
    seed_after = at.sidebar.number_input(key="seed_input").value
    assert seed_after != seed_before, "Seed hat sich durch den Klick nicht geändert"


@pytest.mark.parametrize("slider_idx,value", [(0, 40), (0, 6), (1, 8), (1, 2)])
def test_slider_extremes(slider_idx, value):
    at = fresh_app()
    at.sidebar.slider[slider_idx].set_value(value).run(timeout=TIMEOUT)
    assert_ok(at)


def test_worst_case_settings_no_crash():
    at = fresh_app()
    at.sidebar.slider[0].set_value(40).run(timeout=TIMEOUT)
    at.sidebar.slider[1].set_value(8).run(timeout=TIMEOUT)
    at.sidebar.slider[2].set_value(12).run(timeout=TIMEOUT)
    assert_ok(at)


@pytest.mark.parametrize("prefix", ["star", "greedy"])
def test_animation_toggle(prefix):
    at = fresh_app()
    cb = [c for c in at.checkbox if c.key == f"{prefix}_auto"]
    assert cb
    cb[0].check().run(timeout=TIMEOUT)
    assert_ok(at)


def test_pdf_download_buttons_present():
    at = fresh_app()
    assert_ok(at)
    labels = [d.label for d in at.download_button]
    assert len(labels) == 3  # Primäransicht + Sternnetz + Nachfrage-optimiert
    assert all("PDF" in l for l in labels)


def test_feedback_buttons_work():
    at = fresh_app()
    up = [b for b in at.button if b.key == "feedback_up_btn"][0]
    up.click().run(timeout=TIMEOUT)
    assert_ok(at)
    assert any("Danke" in str(s.value) for s in at.success)


def test_comparison_tab_has_both_methods():
    at = fresh_app()
    assert_ok(at)
    comparison_dfs = [d for d in at.dataframe if "Methode" in d.value.columns]
    assert comparison_dfs
    methods = comparison_dfs[0].value["Methode"].tolist()
    assert "Sternnetz" in methods
    assert "Nachfrage-optimiert" in methods


def test_permalink_writes_and_restores():
    at = fresh_app()
    assert_ok(at)
    qp = dict(at.query_params)
    for key in ["n_stops", "n_lines", "max_len", "hub_conc", "n_hubs", "seed"]:
        assert key in qp

    at2 = AppTest.from_file(APP_PATH)
    at2.query_params["n_stops"] = "22"
    at2.run(timeout=TIMEOUT)
    assert_ok(at2)
    assert at2.sidebar.slider[0].value == 22


@pytest.mark.parametrize("param,value", [
    ("n_stops", "9999"), ("n_stops", "-5"), ("n_lines", "9999"),
    ("hub_conc", "nan"), ("hub_conc", "inf"), ("hub_conc", "-inf"),
    ("seed", "-42"), ("n_lines", "not_a_number"), ("max_len", "9999"),
])
def test_permalink_handles_bad_values_without_crash(param, value):
    """Von Anfang an geprüft (Lehre aus der Tourenplanung-Demo, wo diese
    Absturzklasse erst nachträglich gefunden wurde): Permalink-Werte
    außerhalb des Wertebereichs, ungültigen Typs oder nicht-finite (NaN/Inf)
    dürfen die App nie zum Absturz bringen."""
    at = AppTest.from_file(APP_PATH)
    at.query_params[param] = value
    at.run(timeout=TIMEOUT)
    assert_ok(at)


def test_slider_bounds_match_setting_specs():
    import transit_presets

    at = fresh_app()
    assert_ok(at)
    by_key = {s.key: s for s in at.sidebar.slider if s.key}
    checked = 0
    for state_key, spec in transit_presets.SETTING_SPECS.items():
        if spec.lo is None or state_key not in by_key:
            continue
        slider = by_key[state_key]
        assert slider.min == pytest.approx(spec.lo)
        assert slider.max == pytest.approx(spec.hi)
        checked += 1
    assert checked == 5, f"Nur {checked} von 5 erwarteten Slidern geprüft - Test greift vermutlich nicht vollständig"


def test_setting_specs_defaults_are_within_bounds():
    import transit_presets

    for state_key, spec in transit_presets.SETTING_SPECS.items():
        if spec.lo is not None:
            assert spec.lo <= spec.default <= spec.hi, f"{state_key}: Default außerhalb [{spec.lo},{spec.hi}]"


def test_permalink_url_params_are_unique():
    import transit_presets

    params = [spec.url_param for spec in transit_presets.SETTING_SPECS.values()]
    assert len(params) == len(set(params))


# ==========================================================================
# 2. Unit-Tests der reinen Funktionen
# ==========================================================================

from transit_demand import generate_stops_and_demand
from transit_evaluation import evaluate_network, stops_covered
from transit_heuristics import demand_greedy_construction, star_network_construction


def test_generate_stops_and_demand_shapes_and_symmetry():
    coords, demand, hubs = generate_stops_and_demand(15, seed=1)
    assert coords.shape == (15, 2)
    assert demand.shape == (15, 15)
    assert np.allclose(demand, demand.T)
    assert np.allclose(np.diag(demand), 0)


def test_generate_stops_and_demand_hub_concentration_effect():
    """Höhere hub_concentration sollte einen größeren Anteil der Nachfrage
    auf die Hub-Haltestellen konzentrieren."""
    _, demand_low, hubs_low = generate_stops_and_demand(20, seed=1, hub_concentration=0.0, n_hubs=2)
    _, demand_high, hubs_high = generate_stops_and_demand(20, seed=1, hub_concentration=0.9, n_hubs=2)

    def hub_share(demand, hubs):
        total = demand.sum()
        hub_total = demand[hubs, :].sum() + demand[:, hubs].sum() - demand[hubs][:, hubs].sum()
        return hub_total / total if total > 0 else 0

    assert hub_share(demand_high, hubs_high) > hub_share(demand_low, hubs_low)


def test_generate_stops_and_demand_n_hubs_exceeds_n_stops_handled():
    coords, demand, hubs = generate_stops_and_demand(3, seed=1, n_hubs=10)
    assert len(hubs) <= 3


# --- Umsteige-Bewertungslogik: handkonstruierte Fälle mit bekanntem Ergebnis ---

def test_evaluate_network_direct_one_transfer_unreachable_handconstructed():
    """Kernkorrektheitstest der Demo - gegen ein handkonstruiertes Szenario
    mit bekanntem korrektem Ergebnis geprüft (nicht nur strukturell validiert)."""
    lines = [[0, 1, 2], [2, 3, 4], [5]]
    demand = np.zeros((6, 6))
    pairs = {(0, 1): 10, (0, 2): 20, (0, 3): 30, (0, 5): 40, (1, 3): 15, (2, 4): 5}
    for (i, j), d in pairs.items():
        demand[i][j] = d
        demand[j][i] = d

    result = evaluate_network(lines, demand)
    assert result["total_demand"] == 120
    assert result["direct_demand"] == 35  # (0,1)+(0,2)+(2,4) = 10+20+5
    assert result["one_transfer_demand"] == 45  # (0,3)+(1,3) = 30+15
    assert result["unreachable_demand"] == 40  # (0,5)


def test_evaluate_network_multi_line_transfer_hub():
    """Eine Haltestelle, die auf drei Linien gleichzeitig liegt (großer
    Umsteigeknoten), muss als Umstiegspunkt zwischen allen drei erkannt
    werden."""
    lines = [[0, 2], [2, 3], [2, 4, 5], [6, 7]]
    demand = np.zeros((8, 8))
    demand[0][4], demand[4][0] = 10, 10  # 1 Umstieg über Knoten 2
    demand[0][7], demand[7][0] = 20, 20  # unerreichbar (keine gemeinsame Haltestelle)
    result = evaluate_network(lines, demand)
    assert result["one_transfer_demand"] == 10
    assert result["unreachable_demand"] == 20


def test_evaluate_network_empty_lines_all_unreachable():
    demand = np.zeros((4, 4))
    demand[0][1] = demand[1][0] = 30
    result = evaluate_network([], demand)
    assert result["unreachable_demand"] == 30
    assert result["direct_demand"] == 0


def test_evaluate_network_zero_demand_no_crash():
    result = evaluate_network([[0, 1, 2]], np.zeros((5, 5)))
    assert result["total_demand"] == 0


def test_evaluate_network_touching_only_at_shared_stop_is_transfer_not_direct():
    """Zwei Linien, die sich NUR an einer gemeinsamen Haltestelle berühren,
    dürfen für ein Paar auf verschiedenen Linien nicht als 'direkt' zählen."""
    lines = [[0, 1], [1, 2]]
    demand = np.zeros((3, 3))
    demand[0][2] = demand[2][0] = 10
    result = evaluate_network(lines, demand)
    assert result["direct_demand"] == 0
    assert result["one_transfer_demand"] == 10


def test_stops_covered_counts_unique_stops_across_lines():
    lines = [[0, 1, 2], [2, 3], [4]]
    assert stops_covered(lines, 6) == 5  # 0,1,2,3,4 (5 fehlt)


def test_stops_with_unreachable_demand_was_dead_code_now_wired_up():
    """Regressionstest für einen gefundenen Bug: `highlight_unreachable` war
    in build_network_figure implementiert und verwendet, wurde aber von
    keinem Aufrufer je befüllt - eine halb-fertige, nie sichtbare Funktion.
    Prüft die zugehörige Berechnungsfunktion direkt anhand eines
    handkonstruierten Falls mit bekanntem Ergebnis."""
    from transit_evaluation import stops_with_unreachable_demand

    lines = [[0, 1], [2, 3]]  # zwei unverbundene Linien
    demand = np.zeros((4, 4))
    demand[0][2] = demand[2][0] = 10  # unerreichbar (keine gemeinsame Haltestelle)
    demand[0][1] = demand[1][0] = 5   # direkt erreichbar (beide auf Linie 1)

    affected = stops_with_unreachable_demand(lines, demand)
    assert affected == {0, 2}  # 1 und 3 haben nur die direkte/keine Beziehung


def test_unreachable_highlighting_wired_into_all_map_calls():
    """Stellt sicher, dass die Primäransicht UND beide Detail-Tabs die neu
    verdrahtete Hervorhebung tatsächlich nutzen (nicht nur eine Stelle)."""
    at = fresh_app()
    assert_ok(at)
    captions = [str(c.value) for c in at.caption if "Rot markiert" in str(c.value)]
    assert len(captions) == 2  # ein Panel je Heuristik-Tab (Stern, Nachfrage-optimiert)


# --- Heuristiken: strukturelle Korrektheit ---

def _validate_lines(lines, n_stops, max_line_length):
    for line in lines:
        assert len(line) <= max_line_length
        assert len(set(line)) == len(line), f"Haltestelle mehrfach in Linie: {line}"
        for s in line:
            assert 0 <= s < n_stops


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("heuristic", [star_network_construction, demand_greedy_construction])
def test_heuristics_produce_structurally_valid_lines(heuristic, seed):
    coords, demand, hubs = generate_stops_and_demand(20, seed=seed, hub_concentration=0.6, n_hubs=2)
    lines = heuristic(coords, demand, n_lines=4, max_line_length=7)
    _validate_lines(lines, 20, 7)


def test_star_network_always_fully_connected():
    """Kerneigenschaft des Sternnetzes: da alle Linien den Hub teilen, ist
    jede abgedeckte Haltestelle über höchstens einen Umstieg von jeder
    anderen abgedeckten Haltestelle erreichbar - 0% unerreichbar, sofern
    Nachfrage nur zwischen abgedeckten Haltestellen besteht."""
    coords, demand, hubs = generate_stops_and_demand(20, seed=1, hub_concentration=0.6, n_hubs=2)
    lines = star_network_construction(coords, demand, n_lines=4, max_line_length=7)
    result = evaluate_network(lines, demand)
    assert result["unreachable_pct"] == pytest.approx(0.0, abs=0.01)


def test_demand_greedy_achieves_full_coverage():
    """Regressionstest für einen beim Bauen gefundenen Fehler: ohne
    Wachstumsbonus deckte die nachfrage-getriebene Konstruktion nur einen
    Bruchteil der Haltestellen ab (11 von 20), weil sie sich immer wieder
    auf dieselben wenigen nachfragestarken Haltestellen konzentrierte."""
    coords, demand, hubs = generate_stops_and_demand(20, seed=1, hub_concentration=0.6, n_hubs=2)
    lines = demand_greedy_construction(coords, demand, n_lines=4, max_line_length=7)
    assert stops_covered(lines, 20) == 20


def test_demand_greedy_network_is_connected():
    """Regressionstest für einen beim Bauen gefundenen Fehler: ohne die
    Netzanbindungs-Regel baute die Konstruktion isolierte Teilnetze ohne
    Umsteigemöglichkeit zueinander (53-61% unerreichbar im ursprünglichen
    Benchmark)."""
    coords, demand, hubs = generate_stops_and_demand(20, seed=1, hub_concentration=0.6, n_hubs=2)
    lines = demand_greedy_construction(coords, demand, n_lines=4, max_line_length=7)
    result = evaluate_network(lines, demand)
    assert result["unreachable_pct"] < 5.0


def test_demand_greedy_generally_beats_star_on_direct_connectivity():
    """Qualitäts-Sanity-Check: über mehrere Instanzen sollte die
    nachfrage-optimierte Methode im Schnitt mehr direkte (umstiegsfreie)
    Erreichbarkeit liefern als das Sternnetz - das ist ihr eigentlicher
    Daseinszweck."""
    direct_deltas = []
    for seed in range(1, 6):
        coords, demand, hubs = generate_stops_and_demand(20, seed=seed, hub_concentration=0.6, n_hubs=2)
        lines_star = star_network_construction(coords, demand, n_lines=4, max_line_length=7)
        lines_greedy = demand_greedy_construction(coords, demand, n_lines=4, max_line_length=7)
        direct_deltas.append(
            evaluate_network(lines_greedy, demand)["direct_pct"] - evaluate_network(lines_star, demand)["direct_pct"]
        )
    assert sum(direct_deltas) / len(direct_deltas) > 10.0


def test_heuristics_handle_zero_stops():
    coords, demand = np.zeros((0, 2)), np.zeros((0, 0))
    lines_star = star_network_construction(coords, demand, n_lines=3, max_line_length=5)
    lines_greedy = demand_greedy_construction(coords, demand, n_lines=3, max_line_length=5)
    assert all(len(l) == 0 for l in lines_star)
    assert all(len(l) == 0 for l in lines_greedy)


# --- PDF-Export ---

def test_generate_network_plan_pdf_produces_valid_pdf():
    from transit_pdf_export import generate_network_plan_pdf

    coords, demand, hubs = generate_stops_and_demand(12, seed=2)
    lines = demand_greedy_construction(coords, demand, n_lines=3, max_line_length=6)
    ids = list(range(1, 13))
    pdf_bytes = generate_network_plan_pdf("Test", lines, ids, demand)
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 500


# --- Feedback ---

def test_feedback_log_and_count_roundtrip(tmp_path):
    from transit_feedback import get_feedback_counts, log_feedback

    log_file = str(tmp_path / "feedback_test.csv")
    assert get_feedback_counts(log_file) == (0, 0)
    assert log_feedback("up", log_file) is True
    assert log_feedback("down", log_file) is True
    assert log_feedback("up", log_file) is True
    assert get_feedback_counts(log_file) == (2, 1)
