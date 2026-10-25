"""Workspace jail: paths, symlinks, and secret files."""

import os

import pytest

from tools.jail import JailError, resolve_in_jail


def test_relative_path_stays_in_the_workspace(isolate_pip_files):
    resolved = resolve_in_jail("notes/today.txt")
    root = os.path.realpath(isolate_pip_files / "work")
    assert resolved == os.path.join(root, "notes", "today.txt")


def test_empty_path_is_refused():
    with pytest.raises(JailError, match="required"):
        resolve_in_jail("   ")


def test_parent_escape_is_refused(isolate_pip_files):
    with pytest.raises(JailError, match="outside"):
        resolve_in_jail("../outside.txt")
    outside = isolate_pip_files / "outside.txt"
    outside.write_text("hidden")
    with pytest.raises(JailError, match="outside"):
        resolve_in_jail(str(outside))


def test_symlink_escape_is_refused(isolate_pip_files):
    outside = isolate_pip_files / "outside.txt"
    outside.write_text("hidden")
    link = isolate_pip_files / "work" / "escape"
    link.symlink_to(outside)
    with pytest.raises(JailError, match="outside"):
        resolve_in_jail("escape")


def test_env_file_inside_the_workspace_is_refused(isolate_pip_files):
    with pytest.raises(JailError, match="not available"):
        resolve_in_jail(".env")
    with pytest.raises(JailError, match="not available"):
        resolve_in_jail("nested/.env")


def test_vault_jobs_and_model_config_are_refused_even_inside_the_workspace(isolate_pip_files, monkeypatch):
    root = isolate_pip_files / "work"
    vault = root / "vault.json"
    key = root / "vault.key"
    jobs = root / "jobs.sqlite"
    model = root / "model.json"
    for path in (vault, key, jobs, model):
        path.write_text("secret")
    monkeypatch.setenv("PIP_VAULT_PATH", str(vault))
    monkeypatch.setenv("PIP_VAULT_KEY_FILE", str(key))
    monkeypatch.setenv("PIP_JOBS_PATH", str(jobs))
    monkeypatch.setenv("PIP_MODEL_CONFIG", str(model))
    for name in ("vault.json", "vault.key", "jobs.sqlite", "model.json"):
        with pytest.raises(JailError, match="not available"):
            resolve_in_jail(name)
