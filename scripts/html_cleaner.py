#!/usr/bin/env python3
"""
Batch-clean local HTML files into readable output using Trafilatura.

Defaults:
- Input:  data/html
- Output: data/output

Usage:
  python scripts/html_cleaner.py
  python scripts/html_cleaner.py --overwrite
  python scripts/html_cleaner.py --output-format markdown
  python scripts/html_cleaner.py --input-dir /abs/path/to/data/html --output-dir /abs/path/to/data/output
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

import trafilatura


@dataclass(frozen=True)
class CleanResult:
    input_path: str
    output_path: Optional[str]
    ok: bool
    extracted_chars: int
    error: Optional[str]


def _repo_root() -> Path:
    # scripts/html_cleaner.py -> repo root
    return Path(__file__).resolve().parents[1]


def _iter_html_files(input_dir: Path) -> Iterable[Path]:
    # Support odd filenames (spaces, unicode, etc.) by using Path APIs.
    for suffix in (".html", ".htm"):
        yield from input_dir.rglob(f"*{suffix}")


def _normalize_text(text: str) -> str:
    # Keep it conservative: normalize line endings and collapse excessive blank lines.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in text.split("\n")]

    cleaned: list[str] = []
    blank_run = 0
    for ln in lines:
        if ln.strip() == "":
            blank_run += 1
            if blank_run <= 2:
                cleaned.append("")
            continue
        blank_run = 0
        cleaned.append(ln)

    return "\n".join(cleaned).strip() + "\n"

def _normalize_markdown(md: str) -> str:
    # Avoid aggressively changing Markdown semantics; just normalize line endings
    # and ensure a single trailing newline.
    md = md.replace("\r\n", "\n").replace("\r", "\n")
    return md.strip() + "\n"


def clean_html_file(
    input_file: Path,
    *,
    output_format: str,
    include_tables: bool = True,
    include_comments: bool = False,
) -> str:
    html = input_file.read_text(encoding="utf-8", errors="replace")

    # Trafilatura supports output_format="txt" and "markdown" among others.
    extracted = trafilatura.extract(
        html,
        output_format=output_format,
        include_tables=include_tables,
        include_comments=include_comments,
        with_metadata=False,
    )
    if not extracted:
        raise ValueError("Trafilatura could not extract main text (empty result).")

    if output_format == "txt":
        return _normalize_text(extracted)
    if output_format == "markdown":
        return _normalize_markdown(extracted)
    return extracted


def write_output_text(
    *,
    text: str,
    output_format: str,
    input_dir: Path,
    output_dir: Path,
    input_file: Path,
    overwrite: bool,
) -> Path:
    rel = input_file.relative_to(input_dir)
    ext = ".txt" if output_format == "txt" else ".md"
    out_path = (output_dir / rel).with_suffix(ext)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists() and not overwrite:
        # If the existing file is non-empty, treat it as already processed.
        try:
            if out_path.stat().st_size > 0:
                return out_path
        except OSError:
            # If stat fails for any reason, fall back to overwriting only when asked.
            return out_path

    out_path.write_text(text, encoding="utf-8")
    return out_path


def run_batch(
    *,
    input_dir: Path,
    output_dir: Path,
    output_format: str,
    overwrite: bool,
    limit: Optional[int],
    include_tables: bool,
    include_comments: bool,
) -> list[CleanResult]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[CleanResult] = []
    count = 0

    for html_file in sorted(_iter_html_files(input_dir)):
        if limit is not None and count >= limit:
            break
        count += 1

        try:
            text = clean_html_file(
                html_file,
                output_format=output_format,
                include_tables=include_tables,
                include_comments=include_comments,
            )
            out_path = write_output_text(
                text=text,
                output_format=output_format,
                input_dir=input_dir,
                output_dir=output_dir,
                input_file=html_file,
                overwrite=overwrite,
            )
            results.append(
                CleanResult(
                    input_path=str(html_file),
                    output_path=str(out_path),
                    ok=True,
                    extracted_chars=len(text),
                    error=None,
                )
            )
        except Exception as e:
            results.append(
                CleanResult(
                    input_path=str(html_file),
                    output_path=None,
                    ok=False,
                    extracted_chars=0,
                    error=str(e),
                )
            )

    # Write a manifest for auditing (successes + failures).
    manifest_path = output_dir / "manifest.json"
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "total": len(results),
        "ok": sum(1 for r in results if r.ok),
        "failed": sum(1 for r in results if not r.ok),
        "results": [asdict(r) for r in results],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    logging.info("Wrote manifest: %s", manifest_path)

    return results


def _parse_args(argv: list[str]) -> argparse.Namespace:
    root = _repo_root()
    default_input = root / "data" / "html"
    default_output = root / "data" / "output"

    p = argparse.ArgumentParser(description="Clean local HTML files to plain text using Trafilatura.")
    p.add_argument("--input-dir", type=Path, default=default_input, help="Directory containing .html files")
    p.add_argument("--output-dir", type=Path, default=default_output, help="Directory to write cleaned .txt files")
    p.add_argument(
        "--output-format",
        choices=["markdown", "txt"],
        default="markdown",
        help="Extraction output format (default: markdown)",
    )
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing output files")
    p.add_argument("--limit", type=int, default=None, help="Process only the first N files (for quick tests)")
    p.add_argument("--no-tables", action="store_true", help="Exclude tables from extraction (default includes tables)")
    p.add_argument("--include-comments", action="store_true", help="Include comments in extraction (default excludes)")
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    ns = _parse_args(sys.argv[1:] if argv is None else argv)

    include_tables = not bool(ns.no_tables)
    include_comments = bool(ns.include_comments)

    results = run_batch(
        input_dir=ns.input_dir,
        output_dir=ns.output_dir,
        output_format=str(ns.output_format),
        overwrite=ns.overwrite,
        limit=ns.limit,
        include_tables=include_tables,
        include_comments=include_comments,
    )

    ok = sum(1 for r in results if r.ok)
    failed = sum(1 for r in results if not r.ok)
    logging.info("Done. ok=%s failed=%s (output: %s)", ok, failed, ns.output_dir)

    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
