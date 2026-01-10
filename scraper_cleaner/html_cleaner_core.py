"""Core HTML cleaning functionality extracted from scripts/html_cleaner.py."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

import trafilatura


@dataclass(frozen=True)
class CleanResult:
    """Result of cleaning a single HTML file."""

    input_path: str
    output_path: Optional[str]
    ok: bool
    extracted_chars: int
    error: Optional[str]


def iter_html_files(input_dir: Path) -> Iterable[Path]:
    """Find all HTML files recursively in the input directory.

    Supports odd filenames (spaces, unicode, etc.) by using Path APIs.
    """
    for suffix in (".html", ".htm"):
        yield from input_dir.rglob(f"*{suffix}")


def normalize_text(text: str) -> str:
    """Normalize text: line endings and collapse excessive blank lines."""
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


def normalize_markdown(md: str) -> str:
    """Normalize markdown: line endings and ensure single trailing newline."""
    md = md.replace("\r\n", "\n").replace("\r", "\n")
    return md.strip() + "\n"


def clean_html_file(
    input_file: Path,
    *,
    output_format: str,
    include_tables: bool = True,
    include_comments: bool = False,
) -> str:
    """Clean a single HTML file using Trafilatura.

    Args:
        input_file: Path to the HTML file
        output_format: Output format ("txt" or "markdown")
        include_tables: Whether to include tables in extraction
        include_comments: Whether to include comments in extraction

    Returns:
        Cleaned text content

    Raises:
        ValueError: If extraction fails or returns empty result
    """
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
        return normalize_text(extracted)
    if output_format == "markdown":
        return normalize_markdown(extracted)
    return extracted


def make_flat_filename(relative_path: Path, output_format: str) -> str:
    """Create a flat, collision-safe filename from a relative path.

    Args:
        relative_path: Path relative to input directory (e.g., Path("news/a.html"))
        output_format: Output format ("txt" or "markdown")

    Returns:
        Flat filename with hash (e.g., "news__a__3f2a9c1d.md")
    """
    # Convert path to filesystem-safe string: "news/a.html" -> "news__a__hash.ext"
    parts = list(relative_path.parts)
    # Replace directory separators with double underscore
    base_name = "__".join(parts)
    # Remove extension
    base_name = base_name.rsplit(".", 1)[0] if "." in base_name else base_name

    # Add short hash to prevent collisions (first 8 chars of md5)
    path_str = str(relative_path)
    hash_suffix = hashlib.md5(path_str.encode("utf-8")).hexdigest()[:8]

    ext = ".txt" if output_format == "txt" else ".md"
    return f"{base_name}__{hash_suffix}{ext}"


def write_output_text(
    *,
    text: str,
    output_format: str,
    input_dir: Path,
    output_dir: Path,
    input_file: Path,
    overwrite: bool,
    flat_output: bool = True,
) -> Path:
    """Write cleaned text to output file.

    Args:
        text: Cleaned text content
        output_format: Output format ("txt" or "markdown")
        input_dir: Base input directory (for computing relative paths)
        output_dir: Base output directory
        input_file: Input file path
        overwrite: Whether to overwrite existing files (default True per plan)
        flat_output: Whether to use flat naming (default True per plan)

    Returns:
        Path to the written output file
    """
    if flat_output:
        # Flat output: use hash-based naming
        try:
            rel = input_file.relative_to(input_dir)
        except ValueError:
            # If file is not under input_dir, use its basename
            rel = Path(input_file.name)
        filename = make_flat_filename(rel, output_format)
        out_path = output_dir / filename
    else:
        # Mirror directory structure (legacy behavior)
        rel = input_file.relative_to(input_dir)
        ext = ".txt" if output_format == "txt" else ".md"
        out_path = (output_dir / rel).with_suffix(ext)
        out_path.parent.mkdir(parents=True, exist_ok=True)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Overwrite by default (per plan), but respect --no-overwrite flag
    if out_path.exists() and not overwrite:
        # If the existing file is non-empty, treat it as already processed.
        try:
            if out_path.stat().st_size > 0:
                return out_path
        except OSError:
            # If stat fails for any reason, fall back to not overwriting.
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
    flat_output: bool = True,
    input_files: Optional[list[Path]] = None,
) -> list[CleanResult]:
    """Run batch cleaning on HTML files.

    Args:
        input_dir: Base input directory
        output_dir: Base output directory
        output_format: Output format ("txt" or "markdown")
        overwrite: Whether to overwrite existing files
        limit: Maximum number of files to process (None = all)
        include_tables: Whether to include tables
        include_comments: Whether to include comments
        flat_output: Whether to use flat output naming
        input_files: Specific files to process (if None, finds all in input_dir)

    Returns:
        List of CleanResult objects

    Raises:
        FileNotFoundError: If input directory doesn't exist
    """
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[CleanResult] = []
    count = 0

    # Use provided files or find all HTML files
    if input_files is not None:
        html_files = sorted(input_files)
    else:
        html_files = sorted(iter_html_files(input_dir))

    for html_file in html_files:
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
                flat_output=flat_output,
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
