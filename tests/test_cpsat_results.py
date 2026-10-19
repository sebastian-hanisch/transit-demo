"""Messreihe zum CP-SAT-Modell (data/cpsat_results.json): innere Konsistenz und jede README-Zahl."""

from pathlib import Path

import transit_exact_results as R

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
CP = R.load_cpsat()
AB = CP["ablation"]["varianten"]
SK = {(c["n"], c["k"], c["L"]): c for c in CP["skalierung"]}
st = R.stat_text


def has(text):
    assert text in README, text


def test_structure():
    assert set(AB) == {"Grundmodell", "alles", "exact_size", "lex_symmetry", "compact_reach", "hint", "two_stage", "line_cuts"}
    assert set(SK) == {(10, 3, 5), (12, 3, 6), (12, 4, 5), (14, 4, 6), (16, 4, 6), (20, 4, 7)}
    assert all(c["sekunden"]["n"] == 10 for c in SK.values())


def test_agreement_with_the_enumeration():
    a = CP["uebereinstimmung"]
    assert a["bewiesen"]["k"] == a["bewiesen"]["n"] == a["instanzen"] and a["gleiches_optimum"]["k"] == a["gleiches_optimum"]["n"] == a["instanzen"]
    has(f"Auf {a['instanzen']} kleinen Instanzen")
    has(f"in {a['bewiesen']['k']} von {a['bewiesen']['n']} Fällen und findet in {a['gleiches_optimum']['k']} von {a['gleiches_optimum']['n']} dasselbe Optimum")
    has(f"(Mittel {st(a['sekunden_cpsat'], 2)} s gegen {st(a['sekunden_aufzaehlung'], 2)} s je Instanz)")


def test_the_improvements_save_most_of_the_time():
    g, f = AB["Grundmodell"], AB["alles"]
    assert f["bewiesen"]["k"] >= g["bewiesen"]["k"] and f["summe_sekunden"] < 0.5 * g["summe_sekunden"] and f["sekunden"]["med"] < g["sekunden"]["med"]
    for name in ("lex_symmetry", "line_cuts", "compact_reach"):
        assert AB[name]["summe_sekunden"] > 1.3 * f["summe_sekunden"], name          # jeder dieser drei Bausteine fehlt spürbar
    has(f"beweist von 8 Instanzen mit 10 bis 12 Haltestellen und 3 Linien {g['bewiesen']['k']} in {g['summe_sekunden']:.0f} s")
    has(f"beweist es {f['bewiesen']['k']} in {f['summe_sekunden']:.0f} s, der Median sinkt von {g['sekunden']['med']:.1f} s auf {f['sekunden']['med']:.1f} s".replace(".", ","))
    has(f"steigt die Summe auf {AB['lex_symmetry']['summe_sekunden']:.0f}, {AB['line_cuts']['summe_sekunden']:.0f} bzw. {AB['compact_reach']['summe_sekunden']:.0f} s")
    has(f"(Summe {AB['exact_size']['summe_sekunden']:.0f}, {AB['hint']['summe_sekunden']:.0f} bzw. {AB['two_stage']['summe_sekunden']:.0f} s)")


def test_scaling_rows():
    for (n, k, length), c in SK.items():
        has(f"| {n}, {k}, {length} | {c['bewiesen']['k']} von {c['bewiesen']['n']} | {st(c['sekunden'], 1)} | {st(c['luecke_pp'])} | {st(c['cpsat_direkt'])} % | {st(c['greedy_direkt'])} % | "
            f"{st(c['verbesserung_gegen_greedy'])} | {st(c['greedy_hoechstens_unter_optimum'])} |")
        assert c["cpsat_direkt"]["mean"] >= c["greedy_direkt"]["mean"] - 1e-9                 # CP-SAT ist nie schlechter als die Startlösung der Heuristik
        assert c["schranke"]["mean"] >= c["cpsat_direkt"]["mean"] - 1e-9


def test_proof_limit_statements():
    assert all(SK[key]["bewiesen"]["k"] == 10 for key in ((10, 3, 5), (12, 3, 6)))
    four = [c for key, c in SK.items() if key[1] == 4]
    assert all(c["bewiesen"]["k"] == 0 for c in four)
    gaps = [c["luecke_pp"]["mean"] for c in four]
    gains = [c["verbesserung_gegen_greedy"]["mean"] for c in four]
    has(f"die Lücke bleibt bei {min(gaps):.1f} bis {max(gaps):.1f} Punkten".replace(".", ","))
    has(f"Netze, die {min(gains):.1f} bis {max(gains):.1f} Punkte besser sind".replace(".", ","))
    has(f"höchstens {st(SK[(20, 4, 7)]['greedy_hoechstens_unter_optimum'])} Punkte unter dem Optimum")


def test_file_is_small():
    assert (ROOT / "data" / "cpsat_results.json").stat().st_size < 20_000
