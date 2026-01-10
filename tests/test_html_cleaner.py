import importlib.util
import json
from pathlib import Path
import sys

import pytest


@pytest.fixture(scope="session")
def html_cleaner_module():
    """
    Import scripts/html_cleaner.py reliably, without depending on PYTHONPATH.
    """
    repo_root = Path(__file__).resolve().parents[1]
    target = repo_root / "scripts" / "html_cleaner.py"
    spec = importlib.util.spec_from_file_location("html_cleaner", target)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Needed for dataclasses + string annotations resolution during import.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.unit
def test_normalize_text_basic(html_cleaner_module):
    text = "a\r\n\r\n\r\nb  \r\n\r\n\r\n\r\nc\r"
    out = html_cleaner_module._normalize_text(text)
    # line endings normalized + trailing spaces removed
    assert out.startswith("a\n\n\nb\n\n\nc\n")
    # No more than 2 consecutive blank lines (=> max 3 \n in a row)
    assert "\n\n\n\n" not in out
    # Always ends with exactly one newline
    assert out.endswith("\n")
    assert not out.endswith("\n\n")


@pytest.mark.unit
def test_normalize_markdown_minimal(html_cleaner_module):
    md = "# Title\r\n\r\nText\r\n"
    out = html_cleaner_module._normalize_markdown(md)
    assert out == "# Title\n\nText\n"


@pytest.mark.unit
def test_clean_html_file_calls_trafilatura_extract_with_expected_args(html_cleaner_module, tmp_path, monkeypatch):
    input_file = tmp_path / "a.html"
    input_file.write_text("<html><body><p>Hello</p></body></html>", encoding="utf-8")

    calls = []

    def fake_extract(html, **kwargs):
        calls.append((html, kwargs))
        return "# Hello\n"

    monkeypatch.setattr(html_cleaner_module.trafilatura, "extract", fake_extract)

    out = html_cleaner_module.clean_html_file(
        input_file,
        output_format="markdown",
        include_tables=True,
        include_comments=False,
    )
    assert out == "# Hello\n"
    assert len(calls) == 1
    _, kwargs = calls[0]
    assert kwargs["output_format"] == "markdown"
    assert kwargs["include_tables"] is True
    assert kwargs["include_comments"] is False
    assert kwargs["with_metadata"] is False


@pytest.mark.unit
def test_clean_html_file_raises_on_empty_extraction(html_cleaner_module, tmp_path, monkeypatch):
    input_file = tmp_path / "a.html"
    input_file.write_text("<html><body></body></html>", encoding="utf-8")

    monkeypatch.setattr(html_cleaner_module.trafilatura, "extract", lambda *_args, **_kwargs: None)
    with pytest.raises(ValueError, match="could not extract"):
        html_cleaner_module.clean_html_file(input_file, output_format="txt")


@pytest.mark.unit
def test_write_output_text_preserves_relative_paths_and_extension(html_cleaner_module, tmp_path):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    (input_dir / "sub").mkdir(parents=True)
    input_file = input_dir / "sub" / "a.html"
    input_file.write_text("<html>irrelevant</html>", encoding="utf-8")

    out_path = html_cleaner_module.write_output_text(
        text="# Hello\n",
        output_format="markdown",
        input_dir=input_dir,
        output_dir=output_dir,
        input_file=input_file,
        overwrite=True,
    )
    assert out_path == output_dir / "sub" / "a.md"
    assert out_path.read_text(encoding="utf-8") == "# Hello\n"


@pytest.mark.unit
def test_write_output_text_does_not_overwrite_when_not_requested(html_cleaner_module, tmp_path):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    output_dir.mkdir()
    input_file = input_dir / "a.html"
    input_file.write_text("<html>irrelevant</html>", encoding="utf-8")

    existing = output_dir / "a.md"
    existing.write_text("OLD\n", encoding="utf-8")

    out_path = html_cleaner_module.write_output_text(
        text="NEW\n",
        output_format="markdown",
        input_dir=input_dir,
        output_dir=output_dir,
        input_file=input_file,
        overwrite=False,
    )
    assert out_path == existing
    assert existing.read_text(encoding="utf-8") == "OLD\n"


@pytest.mark.unit
def test_run_batch_writes_outputs_and_manifest(html_cleaner_module, tmp_path, monkeypatch):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    (input_dir / "one.html").write_text("<html>1</html>", encoding="utf-8")
    (input_dir / "two.html").write_text("<html>2</html>", encoding="utf-8")

    # Avoid depending on trafilatura internals here; this test is about batch I/O + manifest.
    monkeypatch.setattr(html_cleaner_module, "clean_html_file", lambda *_a, **_k: "# X\n")

    results = html_cleaner_module.run_batch(
        input_dir=input_dir,
        output_dir=output_dir,
        output_format="markdown",
        overwrite=True,
        limit=None,
        include_tables=True,
        include_comments=False,
    )

    assert len(results) == 2
    assert all(r.ok for r in results)

    assert (output_dir / "one.md").exists()
    assert (output_dir / "two.md").exists()

    manifest_path = output_dir / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["total"] == 2
    assert manifest["ok"] == 2
    assert manifest["failed"] == 0
    assert all(str(p).endswith(".md") for p in [r["output_path"] for r in manifest["results"]])
