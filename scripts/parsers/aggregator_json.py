"""Parser for secondary aggregator rows; provenance remains secondary."""
from .exchange_file import parse_exchange_file


def parse_aggregator_json(payload, **kwargs):
    return parse_exchange_file(payload, **kwargs)
