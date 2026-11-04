"""Investment memo PDF generation (fpdf2)."""

from fpdf import FPDF


def _clean(text: str) -> str:
    return text.encode("latin-1", errors="replace").decode("latin-1")


class MemoPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "Investment Memo", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 10)
        self.cell(
            0, 8,
            "Factual summary from SEC filings. Not financial advice.",
            new_x="LMARGIN", new_y="NEXT",
        )
        self.ln(4)


def build_memo_pdf(ticker: str, question: str, answer: str,
                   sources: list[dict]) -> bytes:
    pdf = MemoPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.multi_cell(0, 8, _clean(f"Ticker: {ticker or 'N/A'}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 7, _clean(f"Question: {question}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, _clean(answer), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Sources", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for src in sources:
        pdf.multi_cell(0, 6, _clean(f"- {src.get('citation', '')}"), new_x="LMARGIN", new_y="NEXT")
        pdf.multi_cell(0, 6, _clean(src.get("text", "")[:400]), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
    return bytes(pdf.output())
