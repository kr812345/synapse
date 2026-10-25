"""Keep unit tests off the real vault, jobs database, and model config."""

import pytest


@pytest.fixture(autouse=True)
def isolate_pip_files(monkeypatch, tmp_path):
    monkeypatch.setenv("PIP_WORK_ROOT", str(tmp_path / "work"))
    monkeypatch.setenv("PIP_VAULT_PATH", str(tmp_path / "vault.json"))
    monkeypatch.setenv("PIP_VAULT_KEY_FILE", str(tmp_path / "vault.key"))
    monkeypatch.setenv("PIP_JOBS_PATH", str(tmp_path / "jobs.sqlite"))
    monkeypatch.setenv("PIP_MODEL_CONFIG", str(tmp_path / "model.json"))
    monkeypatch.delenv("PIP_VAULT_SOCK", raising=False)
    monkeypatch.delenv("PIP_VAULT_ALLOW_CREATE", raising=False)
    (tmp_path / "work").mkdir()
    return tmp_path
