"""File edit stays inside the jail and replaces one occurrence."""

from tools.library.file_tools import FileEdit, FileWrite


async def test_file_edit_replaces_the_first_snippet(isolate_pip_files):
    written = await FileWrite().execute(path="notes.txt", content="alpha alpha")
    assert written.startswith("File successfully written")
    edited = await FileEdit().execute(path="notes.txt", target="alpha", replacement="beta")
    assert edited.startswith("File successfully edited")
    text = (isolate_pip_files / "work" / "notes.txt").read_text(encoding="utf-8")
    assert text == "beta alpha"


async def test_file_edit_reports_a_missing_snippet(isolate_pip_files):
    await FileWrite().execute(path="notes.txt", content="alpha")
    missing = await FileEdit().execute(path="notes.txt", target="nope", replacement="beta")
    assert missing.startswith("Error: Target text not found")


async def test_file_edit_refuses_a_path_outside_the_workspace(isolate_pip_files):
    outside = isolate_pip_files / "outside.txt"
    outside.write_text("hidden", encoding="utf-8")
    refused = await FileEdit().execute(path=str(outside), target="hidden", replacement="nope")
    assert refused.startswith("Error:")
    assert outside.read_text(encoding="utf-8") == "hidden"
