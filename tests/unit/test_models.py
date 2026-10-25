"""Model list and the saved default."""

from tools.library.model_tools import ModelsList, ModelsUse


async def test_models_use_rejects_blank_unknown_and_uninstalled(isolate_pip_files, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    blank = await ModelsUse().execute(model="  ")
    assert blank["status"] == "error"
    unknown = await ModelsUse().execute(model="not-a-model")
    assert unknown["status"] == "error"
    assert "unknown model" in unknown["message"]
    listed = await ModelsList().execute()
    by_id = {row["id"]: row for row in listed["models"]}
    assert by_id["anthropic-api"]["installed"] is False
    assert by_id["gemini-2.5-flash"]["installed"] is True
    missing = await ModelsUse().execute(model="anthropic-api")
    assert missing["status"] == "error"
    assert "not installed" in missing["message"]
    again = await ModelsList().execute()
    assert again["default"] in (None, "")


async def test_models_use_selects_gemini_and_list_marks_it(isolate_pip_files):
    chosen = await ModelsUse().execute(model="Gemini Flash")
    assert chosen["status"] == "ok"
    assert chosen["default"] == "gemini-2.5-flash"
    listed = await ModelsList().execute()
    assert listed["default"] == "gemini-2.5-flash"
    selected = [row for row in listed["models"] if row["selected"]]
    assert [row["id"] for row in selected] == ["gemini-2.5-flash"]
    assert all("key" not in row for row in listed["models"])
