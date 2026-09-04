"""
Erzeugt einen Liniennetzplan als downloadbares PDF (in-memory) - Zusammen-
fassung der Servicequalität + Haltestellenliste je Linie.
"""

import time

from transit_evaluation import evaluate_network


def generate_network_plan_pdf(label, lines, ids, demand):
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    stats = evaluate_network(lines, demand)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Liniennetzplan - {label}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Erstellt: {time.strftime('%d.%m.%Y %H:%M')} Uhr", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Servicequalität", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Ohne Umstieg erreichbar: {stats['direct_pct']:.1f}% der Nachfrage", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Mit einem Umstieg erreichbar: {stats['one_transfer_pct']:.1f}% der Nachfrage", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Nicht erreichbar (>1 Umstieg nötig): {stats['unreachable_pct']:.1f}% der Nachfrage", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Anzahl Linien: {sum(1 for l in lines if l)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    for idx, line in enumerate(lines):
        if not line:
            continue
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, f"Linie {idx + 1} ({len(line)} Haltestellen)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 10)
        stop_names = " -> ".join(str(ids[s]) for s in line)
        pdf.multi_cell(0, 6, stop_names)
        pdf.ln(3)

    return bytes(pdf.output())
