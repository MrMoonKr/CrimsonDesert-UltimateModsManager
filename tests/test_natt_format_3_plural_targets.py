"""is_natt_format_3 must accept the plural ``targets`` dialect.

Bug 2026-05-08 (jhs9354 on Nexus, mod 725 page comment): a Format 3
mod ships TWO .json files; CDUMM reads one and silently ignores the
other. Root cause is that ``is_natt_format_3`` only recognises the
singular dialect (``"target"`` string + top-level ``"intents"``
list) but the spec also defines a plural dialect that bundles
multiple .pabgb targets in one file::

    {"format": 3,
     "targets": [
       {"file": "iteminfo.pabgb", "intents": [...]},
       {"file": "skill.pabgb",    "intents": [...]}
     ]}

``parse_format3_mod_targets`` already parses the plural shape
correctly (see src/cdumm/engine/format3_handler.py:240-307). The
detection function never delegated to it, so a plural-form file
fails ``is_natt_format_3`` -> import_handler routes it past the
Format 3 branch -> falls through as "no recognized format". For
mod 725 one of the two files used the plural dialect, the other
the singular dialect, so only one was picked up.

Fix: ``is_natt_format_3`` accepts either dialect.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def _write(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_detector_accepts_plural_targets_dialect(tmp_path: Path):
    """Plural shape with `targets` list must be recognised as
    Format 3 — same as the singular shape with `target`/`intents`."""
    from cdumm.engine.json_patch_handler import is_natt_format_3

    plural = _write(tmp_path / "plural.json", {
        "format": 3,
        "targets": [
            {"file": "iteminfo.pabgb",
             "intents": [{"entry": "Foo", "key": 100,
                          "field": "max_stack_count",
                          "op": "set", "new": 999}]},
            {"file": "skill.pabgb",
             "intents": [{"entry": "Bar", "key": 200,
                          "field": "cooltime",
                          "op": "set", "new": 0}]},
        ],
    })
    assert is_natt_format_3(plural) is True, (
        "is_natt_format_3 must recognise the plural-targets dialect; "
        "parse_format3_mod_targets already supports it downstream"
    )


def test_singular_dialect_still_recognised(tmp_path: Path):
    """Sanity: the existing singular dialect must still be
    accepted after the plural-shape fix."""
    from cdumm.engine.json_patch_handler import is_natt_format_3

    singular = _write(tmp_path / "singular.json", {
        "format": 3,
        "target": "iteminfo.pabgb",
        "intents": [{"entry": "Foo", "key": 100,
                     "field": "max_stack_count",
                     "op": "set", "new": 999}],
    })
    assert is_natt_format_3(singular) is True


def test_neither_dialect_still_rejected(tmp_path: Path):
    """Sanity: a `format: 3` doc with NEITHER singular nor plural
    keys is still rejected (it's malformed)."""
    from cdumm.engine.json_patch_handler import is_natt_format_3

    bad = _write(tmp_path / "bad.json", {
        "format": 3,
        "comment": "missing both target/targets and intents",
    })
    assert is_natt_format_3(bad) is False


def test_plural_with_non_list_targets_rejected(tmp_path: Path):
    """A `targets` value that is not a list (e.g. dict, string) is
    not a valid plural-shape file — should be rejected."""
    from cdumm.engine.json_patch_handler import is_natt_format_3

    bad = _write(tmp_path / "bad.json", {
        "format": 3,
        "targets": {"file": "x.pabgb", "intents": []},
    })
    assert is_natt_format_3(bad) is False


def test_plural_with_empty_targets_list_rejected(tmp_path: Path):
    """An empty `targets` list is not a valid mod (no work to do).
    Detection must reject it so the importer can surface a
    'malformed Format 3' error instead of routing it through."""
    from cdumm.engine.json_patch_handler import is_natt_format_3

    empty = _write(tmp_path / "empty.json", {
        "format": 3,
        "targets": [],
    })
    assert is_natt_format_3(empty) is False
