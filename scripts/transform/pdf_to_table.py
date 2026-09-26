"""Optional PDF extraction boundary; PDF output must retain page provenance."""


def pdf_to_rows(path):
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError("PDF normalization requires the optional pdf extra") from exc
    rows = []
    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            for row in page.extract_tables() or []:
                rows.extend({"page": page_number, "row": values} for values in row)
    return rows
