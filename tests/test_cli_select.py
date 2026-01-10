from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

import scraper_cleaner.cli.html_cleaner as cli


runner = CliRunner()


@pytest.mark.unit
def test_select_exits_cleanly_when_prompt_returns_none(tmp_path: Path, monkeypatch):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    output_dir.mkdir()
    (input_dir / "a.html").write_text("<html>ok</html>", encoding="utf-8")

    monkeypatch.setattr(cli, "iter_html_files", lambda _p: [input_dir / "a.html"])
    monkeypatch.setattr(
        cli.questionary,
        "checkbox",
        lambda *_a, **_k: SimpleNamespace(ask=lambda: None),
    )

    res = runner.invoke(
        cli.app,
        ["select", "--input-dir", str(input_dir), "--output-dir", str(output_dir)],
    )
    assert res.exit_code == 0
    assert "Selection cancelled" in res.output


@pytest.mark.unit
def test_select_exits_when_no_files_selected(tmp_path: Path, monkeypatch):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    output_dir.mkdir()
    (input_dir / "a.html").write_text("<html>ok</html>", encoding="utf-8")

    monkeypatch.setattr(cli, "iter_html_files", lambda _p: [input_dir / "a.html"])
    monkeypatch.setattr(
        cli.questionary,
        "checkbox",
        lambda *_a, **_k: SimpleNamespace(ask=lambda: []),
    )

    res = runner.invoke(
        cli.app,
        ["select", "--input-dir", str(input_dir), "--output-dir", str(output_dir)],
    )
    assert res.exit_code == 0
    assert "No files selected" in res.output


@pytest.mark.unit
def test_select_coerces_prompt_values_to_paths(tmp_path: Path, monkeypatch):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    output_dir.mkdir()
    selected_file = input_dir / "sub" / "a.html"
    selected_file.parent.mkdir(parents=True)
    selected_file.write_text("<html>ok</html>", encoding="utf-8")

    monkeypatch.setattr(cli, "iter_html_files", lambda _p: [selected_file])
    monkeypatch.setattr(
        cli.questionary,
        "checkbox",
        lambda *_a, **_k: SimpleNamespace(ask=lambda: ["sub/a.html"]),
    )

    called: dict[str, object] = {}

    def fake_run_batch(**kwargs):
        called.update(kwargs)
        return []

    monkeypatch.setattr(cli, "run_batch", fake_run_batch)

    res = runner.invoke(
        cli.app,
        ["select", "--input-dir", str(input_dir), "--output-dir", str(output_dir)],
    )
    assert res.exit_code == 0

    assert "input_files" in called
    assert called["input_files"] == [selected_file.resolve()]

