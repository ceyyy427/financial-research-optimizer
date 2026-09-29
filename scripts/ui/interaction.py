"""Load the bundled offline interaction script for HTML embedding."""
from pathlib import Path


def interaction_js():
    return (Path(__file__).with_name("interaction.js")).read_text(encoding="utf-8")
