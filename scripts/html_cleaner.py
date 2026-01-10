#!/usr/bin/env python3
"""
Backwards-compatible wrapper for scripts/html_cleaner.py.

This script delegates to the new Typer-based CLI while maintaining
backwards compatibility with the original argparse interface.

Usage (legacy):
  python scripts/html_cleaner.py
  python scripts/html_cleaner.py --overwrite
  python scripts/html_cleaner.py --output-format markdown
  python scripts/html_cleaner.py --input-dir /abs/path/to/data/html --output-dir /abs/path/to/data/output

Recommended (after pipx install):
  html-cleaner
  html-cleaner batch
  html-cleaner select
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Import from the new package module
from scraper_cleaner.html_cleaner_core import (
    CleanResult,
    iter_html_files,
    run_batch,
)


def _repo_root() -> Path:
    """Get repository root directory."""
    return Path(__file__).resolve().parents[1]


def main(argv: Optional[list[str]] = None) -> int:
    """Legacy argparse-based main function for backwards compatibility."""
    import argparse

    root = _repo_root()
    default_input = root / "data" / "html"
    default_output = root / "data" / "output"

    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    p = argparse.ArgumentParser(
        description="Clean local HTML files to plain text using Trafilatura. "
        "Note: For interactive selection and better UX, use 'html-cleaner' command after pipx install."
    )
    p.add_argument("--input-dir", type=Path, default=default_input, help="Directory containing .html files")
    p.add_argument("--output-dir", type=Path, default=default_output, help="Directory to write cleaned .txt files")
    p.add_argument(
        "--output-format",
        choices=["markdown", "txt"],
        default="markdown",
        help="Extraction output format (default: markdown)",
    )
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing output files (default: skip)")
    p.add_argument("--limit", type=int, default=None, help="Process only the first N files (for quick tests)")
    p.add_argument("--no-tables", action="store_true", help="Exclude tables from extraction (default includes tables)")
    p.add_argument("--include-comments", action="store_true", help="Include comments in extraction (default excludes)")
    ns = p.parse_args(sys.argv[1:] if argv is None else argv)

    include_tables = not bool(ns.no_tables)
    include_comments = bool(ns.include_comments)

    # Note: Legacy behavior uses flat_output=False to preserve directory structure
    # This maintains backwards compatibility for existing workflows
    results = run_batch(
        input_dir=ns.input_dir,
        output_dir=ns.output_dir,
        output_format=str(ns.output_format),
        overwrite=ns.overwrite,  # Legacy: defaults to False
        limit=ns.limit,
        include_tables=include_tables,
        include_comments=include_comments,
        flat_output=False,  # Legacy: preserve directory structure
    )

    ok = sum(1 for r in results if r.ok)
    failed = sum(1 for r in results if not r.ok)
    logging.info("Done. ok=%s failed=%s (output: %s)", ok, failed, ns.output_dir)

    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
