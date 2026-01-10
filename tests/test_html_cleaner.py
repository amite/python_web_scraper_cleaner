import json
from pathlib import Path

import pytest

from scraper_cleaner.html_cleaner_core import (
    clean_html_file,
    iter_html_files,
    make_flat_filename,
    normalize_markdown,
    normalize_text,
    run_batch,
    write_output_text,
)


@pytest.mark.unit
def test_normalize_text_basic():
    text = "a\r\n\r\n\r\nb  \r\n\r\n\r\n\r\nc\r"
    out = normalize_text(text)
    # line endings normalized + trailing spaces removed
    assert out.startswith("a\n\n\nb\n\n\nc\n")
    # No more than 2 consecutive blank lines (=> max 3 \n in a row)
    assert "\n\n\n\n" not in out
    # Always ends with exactly one newline
    assert out.endswith("\n")
    assert not out.endswith("\n\n")


@pytest.mark.unit
def test_normalize_markdown_minimal():
    md = "# Title\r\n\r\nText\r\n"
    out = normalize_markdown(md)
    assert out == "# Title\n\nText\n"


@pytest.mark.unit
def test_clean_html_file_calls_trafilatura_extract_with_expected_args(tmp_path, monkeypatch):
    input_file = tmp_path / "a.html"
    input_file.write_text("<html><body><p>Hello</p></body></html>", encoding="utf-8")

    import trafilatura

    calls = []

    def fake_extract(html, **kwargs):
        calls.append((html, kwargs))
        return "# Hello\n"

    monkeypatch.setattr(trafilatura, "extract", fake_extract)

    out = clean_html_file(
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
def test_clean_html_file_raises_on_empty_extraction(tmp_path, monkeypatch):
    input_file = tmp_path / "a.html"
    input_file.write_text("<html><body></body></html>", encoding="utf-8")

    import trafilatura

    monkeypatch.setattr(trafilatura, "extract", lambda *_args, **_kwargs: None)
    with pytest.raises(ValueError, match="could not extract"):
        clean_html_file(input_file, output_format="txt")


@pytest.mark.unit
def test_write_output_text_preserves_relative_paths_legacy_mode(tmp_path):
    """Test legacy behavior with flat_output=False (preserves directory structure)."""
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    (input_dir / "sub").mkdir(parents=True)
    input_file = input_dir / "sub" / "a.html"
    input_file.write_text("<html>irrelevant</html>", encoding="utf-8")

    out_path = write_output_text(
        text="# Hello\n",
        output_format="markdown",
        input_dir=input_dir,
        output_dir=output_dir,
        input_file=input_file,
        overwrite=True,
        flat_output=False,  # Legacy mode
    )
    assert out_path == output_dir / "sub" / "a.md"
    assert out_path.read_text(encoding="utf-8") == "# Hello\n"


@pytest.mark.unit
def test_write_output_text_flat_mode(tmp_path):
    """Test new flat output mode with hash-based naming."""
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    (input_dir / "sub").mkdir(parents=True)
    input_file = input_dir / "sub" / "a.html"
    input_file.write_text("<html>irrelevant</html>", encoding="utf-8")

    out_path = write_output_text(
        text="# Hello\n",
        output_format="markdown",
        input_dir=input_dir,
        output_dir=output_dir,
        input_file=input_file,
        overwrite=True,
        flat_output=True,  # New flat mode
    )
    # Should be in output_dir root, not in sub/
    assert out_path.parent == output_dir
    # Should have flat naming: sub__a__<hash>.md
    assert out_path.name.startswith("sub__a__")
    assert out_path.name.endswith(".md")
    assert len(out_path.name) > len("sub__a__.md")  # Has hash
    assert out_path.read_text(encoding="utf-8") == "# Hello\n"


@pytest.mark.unit
def test_write_output_text_does_not_overwrite_when_not_requested(tmp_path):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    output_dir.mkdir()
    input_file = input_dir / "a.html"
    input_file.write_text("<html>irrelevant</html>", encoding="utf-8")

    existing = output_dir / "a.md"
    existing.write_text("OLD\n", encoding="utf-8")

    out_path = write_output_text(
        text="NEW\n",
        output_format="markdown",
        input_dir=input_dir,
        output_dir=output_dir,
        input_file=input_file,
        overwrite=False,
        flat_output=False,  # Legacy mode for this test
    )
    assert out_path == existing
    assert existing.read_text(encoding="utf-8") == "OLD\n"


@pytest.mark.unit
def test_make_flat_filename():
    """Test flat filename generation with hash."""
    rel_path = Path("news/article.html")
    filename = make_flat_filename(rel_path, "markdown")
    # Should be: news__article__<hash>.md
    assert filename.startswith("news__article__")
    assert filename.endswith(".md")
    assert len(filename) > len("news__article__.md")  # Has 8-char hash

    # Same input should produce same hash
    filename2 = make_flat_filename(rel_path, "markdown")
    assert filename == filename2

    # Different input should produce different hash
    rel_path2 = Path("news/article2.html")
    filename3 = make_flat_filename(rel_path2, "markdown")
    assert filename != filename3

    # Test txt format
    filename_txt = make_flat_filename(rel_path, "txt")
    assert filename_txt.endswith(".txt")
    assert filename_txt != filename


@pytest.mark.unit
def test_make_flat_filename_collision_safety():
    """Test that different paths produce different hashes even if base names are similar."""
    path1 = Path("a/b/file.html")
    path2 = Path("a/b/file.htm")
    filename1 = make_flat_filename(path1, "markdown")
    filename2 = make_flat_filename(path2, "markdown")
    # Should be different due to hash
    assert filename1 != filename2


@pytest.mark.unit
def test_run_batch_writes_outputs_and_manifest_flat_mode(tmp_path, monkeypatch):
    """Test batch processing with flat output mode."""
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    (input_dir / "one.html").write_text("<html>1</html>", encoding="utf-8")
    (input_dir / "two.html").write_text("<html>2</html>", encoding="utf-8")

    # Avoid depending on trafilatura internals here; this test is about batch I/O + manifest.
    monkeypatch.setattr(
        "scraper_cleaner.html_cleaner_core.clean_html_file", lambda *_a, **_k: "# X\n"
    )

    results = run_batch(
        input_dir=input_dir,
        output_dir=output_dir,
        output_format="markdown",
        overwrite=True,
        limit=None,
        include_tables=True,
        include_comments=False,
        flat_output=True,
    )

    assert len(results) == 2
    assert all(r.ok for r in results)

    # Files should be in output_dir root (flat mode)
    output_files = list(output_dir.glob("*.md"))
    assert len(output_files) == 2

    manifest_path = output_dir / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["total"] == 2
    assert manifest["ok"] == 2
    assert manifest["failed"] == 0
    assert all(str(p).endswith(".md") for p in [r["output_path"] for r in manifest["results"]])


@pytest.mark.unit
def test_iter_html_files(tmp_path):
    """Test HTML file iteration."""
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    (input_dir / "a.html").write_text("<html>a</html>", encoding="utf-8")
    (input_dir / "b.htm").write_text("<html>b</html>", encoding="utf-8")
    (input_dir / "c.txt").write_text("not html", encoding="utf-8")
    (input_dir / "sub").mkdir()
    (input_dir / "sub" / "d.html").write_text("<html>d</html>", encoding="utf-8")

    files = sorted(iter_html_files(input_dir))
    assert len(files) == 3
    assert (input_dir / "a.html") in files
    assert (input_dir / "b.htm") in files
    assert (input_dir / "sub" / "d.html") in files
    assert (input_dir / "c.txt") not in files
