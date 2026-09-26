"""Minimal HTML table extractor for browser snapshots."""
from html.parser import HTMLParser


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.current = []
        elif tag in {"td", "th"} and self.current is not None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data.strip())

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.current is not None and self.cell is not None:
            self.current.append(" ".join(part for part in self.cell if part))
            self.cell = None
        elif tag == "tr" and self.current is not None:
            if self.current:
                self.rows.append(self.current)
            self.current = None


def html_tables(html_text):
    parser = _TableParser()
    parser.feed(html_text)
    return parser.rows
