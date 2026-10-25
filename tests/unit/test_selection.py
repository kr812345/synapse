"""Saved model default."""

import json

from models.selection import read_default, write_default


def test_missing_config_has_no_default(isolate_pip_files):
    assert read_default() is None


def test_write_then_read_round_trip(isolate_pip_files):
    path = write_default("gemini-2.5-flash")
    assert json.loads(open(path, encoding="utf-8").read()) == {"default": "gemini-2.5-flash"}
    assert read_default() == "gemini-2.5-flash"


def test_broken_config_is_ignored(isolate_pip_files):
    path = isolate_pip_files / "model.json"
    path.write_text("{", encoding="utf-8")
    assert read_default() is None
    path.write_text('{"default": "  "}', encoding="utf-8")
    assert read_default() is None
