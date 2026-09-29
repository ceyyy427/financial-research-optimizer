"""Optional PDF-to-SVG conversion; no fake SVG is emitted on failure."""
from shutil import which


def converter_available():
    return bool(which("pdf2svg") or which("dvisvgm"))
