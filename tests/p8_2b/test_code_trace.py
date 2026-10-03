from __future__ import annotations

import pytest

from finahinking.p8_2b.catalog import get_knowledge_unit
from finahinking.p8_2b.code import select_code_segment, trace_code_to_data


def test_code_segment_links_line_range_to_equation_feature_and_data() -> None:
    segment = select_code_segment(get_knowledge_unit("momentum"), "momentum-code")
    trace = trace_code_to_data(get_knowledge_unit("momentum"), segment.segment_id)
    assert trace["line_range"] == [1, 1]
    assert trace["equation_ids"] == ["momentum-return"]
    assert trace["data_input"] == "price history and lookback"


def test_code_segment_selection_rejects_unknown_or_unsafe_content() -> None:
    with pytest.raises(KeyError):
        select_code_segment(get_knowledge_unit("momentum"), "missing")
    with pytest.raises(ValueError, match="unsafe"):
        select_code_segment(get_knowledge_unit("momentum"), "momentum-code", source_override="import os")
