"""Privacy redaction is a normal production operation, not an ad-hoc ffmpeg spell."""

from __future__ import annotations

import json

import pytest

from chatmonteur.core.errors import ToolError
from chatmonteur.tools.redact import _filter_chain, _load_plan


def _write(tmp_path, payload):  # noqa: ANN001
    path = tmp_path / "redactions.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_redaction_plan_uses_resolution_independent_geometry(tmp_path) -> None:
    items = _load_plan(_write(tmp_path, {
        "redactions": [{
            "start": 24.0,
            "end": 63.0,
            "x": 0.42,
            "y": 0.16,
            "width": 0.42,
            "height": 0.045,
        }]
    }))

    assert items == [{
        "start": 24.0,
        "end": 63.0,
        "x": 0.42,
        "y": 0.16,
        "width": 0.42,
        "height": 0.045,
        "color": "0x0B0B0C",
    }]

    graph = _filter_chain(items)
    assert "drawbox=x=iw*0.42:y=ih*0.16:w=iw*0.42:h=ih*0.045" in graph
    assert "t=fill" in graph
    assert "enable='between(t,24.0,63.0)'" in graph


@pytest.mark.parametrize(
    "patch, message",
    [
        ({"end": 1.0, "start": 2.0}, "after start"),
        ({"x": -0.1}, "x"),
        ({"width": 0.9, "x": 0.2}, "frame"),
        ({"height": 0.0}, "height"),
    ],
)
def test_redaction_plan_refuses_unsafe_or_impossible_boxes(tmp_path, patch, message) -> None:
    item = {
        "start": 1.0,
        "end": 2.0,
        "x": 0.1,
        "y": 0.1,
        "width": 0.2,
        "height": 0.1,
    }
    item.update(patch)

    with pytest.raises(ToolError, match=message):
        _load_plan(_write(tmp_path, {"redactions": [item]}))
