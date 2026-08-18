"""
Ein-Klick-Beispielszenarien und Permalink-Logik - dasselbe SETTING_SPECS-
Muster wie in den anderen beiden Demos: eine Wahrheitsquelle für
Wertebereiche, aus der sowohl die Slider als auch die Permalink-Begrenzung
lesen. Anders als bei der Tourenplanung-Demo von Anfang an so gebaut statt
erst nachträglich - inklusive NaN/Infinity-Schutz.
"""

import math
import random
from dataclasses import dataclass
from typing import Callable, Optional

import streamlit as st

from transit_constants import DEFAULT_MAX_LINE_LENGTH, DEFAULT_N_LINES, DEFAULT_N_STOPS


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: Callable
    default: object
    lo: Optional[float] = None
    hi: Optional[float] = None


SETTING_SPECS = {
    "n_stops_slider": SettingSpec("n_stops", int, DEFAULT_N_STOPS, 6, 40),
    "n_lines_slider": SettingSpec("n_lines", int, DEFAULT_N_LINES, 2, 8),
    "max_line_length_slider": SettingSpec("max_len", int, DEFAULT_MAX_LINE_LENGTH, 3, 12),
    "hub_concentration_slider": SettingSpec("hub_conc", float, 0.5, 0.0, 1.0),
    "n_hubs_slider": SettingSpec("n_hubs", int, 2, 1, 4),
    "seed_input": SettingSpec("seed", int, 42, 0, 2_000_000_000),
}


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def apply_preset(n_stops_val, n_lines_val, max_len_val, hub_conc_val, n_hubs_val, seed_val):
    st.session_state["n_stops_slider"] = n_stops_val
    st.session_state["n_lines_slider"] = n_lines_val
    st.session_state["max_line_length_slider"] = max_len_val
    st.session_state["hub_concentration_slider"] = hub_conc_val
    st.session_state["n_hubs_slider"] = n_hubs_val
    st.session_state["seed_input"] = seed_val
    st.session_state["force_regen"] = True


def randomize_seed():
    """on_click-Callback für den 'Neues Szenario generieren'-Button.

    Auf Nutzerhinweis korrigiert (identischer Fehler wie beim analogen VRP-
    und Fracht-Button, siehe dortige Historie): der Button rief zuvor nur
    ein normales st.button() auf, dessen Wert zwar in die gen_key-
    Neuberechnung einfloss, aber bei UNVERÄNDERTEM Seed erzeugt die
    deterministische Zufallserzeugung dieselben Werte erneut - ein Klick
    bewirkte sichtbar GAR NICHTS, wenn man nicht zusätzlich selbst eine
    neue Seed-Zahl eintippte. Jetzt würfelt der Klick selbst einen neuen,
    zufälligen Seed - ein Klick liefert garantiert ein komplett neues
    Szenario."""
    st.session_state["seed_input"] = random.randint(0, 2_000_000_000)
    st.session_state["force_regen"] = True


def load_permalink_settings():
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    applied_any = False
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            try:
                value = spec.caster(qp[spec.url_param])
                if isinstance(value, float) and not math.isfinite(value):
                    continue
                if spec.lo is not None:
                    value = max(spec.lo, value)
                if spec.hi is not None:
                    value = min(spec.hi, value)
                st.session_state[state_key] = value
                applied_any = True
            except (ValueError, TypeError):
                pass
    if applied_any:
        st.session_state["force_regen"] = True
    st.session_state["permalink_loaded"] = True


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def sync_query_params(n_stops, n_lines, max_line_length, hub_concentration, n_hubs, seed):
    try:
        st.query_params["n_stops"] = str(n_stops)
        st.query_params["n_lines"] = str(n_lines)
        st.query_params["max_len"] = str(max_line_length)
        st.query_params["hub_conc"] = str(hub_concentration)
        st.query_params["n_hubs"] = str(n_hubs)
        st.query_params["seed"] = str(int(seed))
    except Exception:
        pass
