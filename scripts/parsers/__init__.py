"""Parser registry: parser names in source profiles must resolve to code."""
from .aggregator_json import parse_aggregator_json
from .exchange_file import parse_exchange_file
from .fred_json import parse_fred_json
from .sec_xbrl import parse_sec_xbrl
from .stats_gov_json import parse_stats_gov_json
from .sdmx import parse_sdmx
from .tonghuashun_jsonp import parse_tonghuashun_jsonp


PARSERS = {
    "stats_gov_json": parse_stats_gov_json,
    "fred_json": parse_fred_json,
    "fred_json_realtime_period": parse_fred_json,
    "sec_xbrl_filing": parse_sec_xbrl,
    "exchange_file_v1": parse_exchange_file,
    "aggregator_json": parse_aggregator_json,
    "aggregator_html_json": parse_aggregator_json,
    "chart_data_json": parse_aggregator_json,
    "ecb_sdmx_json": parse_sdmx,
    "bis_sdmx_json": parse_sdmx,
    "tonghuashun_jsonp": parse_tonghuashun_jsonp,
}


def get_parser(name):
    return PARSERS.get(name)


def parse(name, payload, **kwargs):
    parser = get_parser(name)
    if parser is None:
        raise KeyError(f"parser unavailable: {name}")
    return parser(payload, **kwargs)
