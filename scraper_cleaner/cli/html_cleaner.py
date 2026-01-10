"""Typer-based CLI for html-cleaner command."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

import questionary
import typer
from rich.console import Console
from rich.logging import RichHandler

from scraper_cleaner.html_cleaner_core import (
    CleanResult,
    clean_html_file,
    iter_html_files,
    run_batch,
    write_output_text,
)

app = typer.Typer(
    name="html-cleaner",
    help="Clean HTML files into readable markdown/text using Trafilatura",
    no_args_is_help=False,
)
console = Console()


def setup_logging(level: str = "INFO") -> None:
    """Setup logging with Rich handler."""
    logging.basicConfig(
        level=level.upper(),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


def get_default_input_dir() -> Path:
    """Get default input directory (cwd-relative)."""
    return Path.cwd() / "data" / "html"


def get_default_output_dir() -> Path:
    """Get default output directory (cwd-relative)."""
    return Path.cwd() / "data" / "output"


def format_output_format(format_str: str) -> str:
    """Validate and normalize output format."""
    if format_str.lower() in ("markdown", "md"):
        return "markdown"
    if format_str.lower() in ("txt", "text"):
        return "txt"
    raise typer.BadParameter(f"Output format must be 'markdown' or 'txt', got: {format_str}")


@app.command()
def batch(
    input_dir: Path = typer.Option(
        None,
        "--input-dir",
        "-i",
        help="Directory containing HTML files (default: ./data/html)",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    output_dir: Path = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Directory to write cleaned files (default: ./data/output)",
        file_okay=False,
        dir_okay=True,
    ),
    output_format: str = typer.Option(
        "markdown",
        "--output-format",
        "-f",
        help="Output format: markdown or txt",
    ),
    overwrite: bool = typer.Option(
        True,
        "--overwrite/--no-overwrite",
        help="Overwrite existing output files (default: overwrite)",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-n",
        help="Process only the first N files (for quick tests)",
    ),
    no_tables: bool = typer.Option(
        False,
        "--no-tables/--tables",
        help="Exclude tables from extraction (default includes tables)",
    ),
    include_comments: bool = typer.Option(
        False,
        "--include-comments/--no-comments",
        help="Include comments in extraction (default excludes)",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        help="Logging level: DEBUG, INFO, WARNING, ERROR",
    ),
) -> None:
    """Batch-process a directory of HTML files."""
    setup_logging(log_level)

    input_path = input_dir or get_default_input_dir()
    output_path = output_dir or get_default_output_dir()

    try:
        format_normalized = format_output_format(output_format)
    except typer.BadParameter as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if not input_path.exists():
        console.print(f"[red]Error:[/red] Input directory does not exist: {input_path}")
        raise typer.Exit(1)

    logger = logging.getLogger(__name__)
    logger.info(f"Processing HTML files from: {input_path}")
    logger.info(f"Output directory: {output_path}")
    logger.info(f"Format: {format_normalized}, Overwrite: {overwrite}")

    try:
        results = run_batch(
            input_dir=input_path,
            output_dir=output_path,
            output_format=format_normalized,
            overwrite=overwrite,
            limit=limit,
            include_tables=not no_tables,
            include_comments=include_comments,
            flat_output=True,
        )

        ok = sum(1 for r in results if r.ok)
        failed = sum(1 for r in results if not r.ok)

        logger.info(f"Done. Processed: {len(results)}, Success: {ok}, Failed: {failed}")
        if failed > 0:
            logger.warning("Some files failed to process:")
            for r in results:
                if not r.ok:
                    logger.warning(f"  - {r.input_path}: {r.error}")

        raise typer.Exit(0 if failed == 0 else 1)

    except Exception as e:
        logger.error(f"Batch processing failed: {e}", exc_info=True)
        raise typer.Exit(2)


@app.command()
def file(
    input_file: Path = typer.Argument(
        ...,
        help="Input HTML file to process",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        help="Output file path (if not provided, writes to --output-dir with flat naming)",
        file_okay=True,
        dir_okay=False,
    ),
    output_dir: Path = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Output directory (default: ./data/output, used if --output not provided)",
        file_okay=False,
        dir_okay=True,
    ),
    output_format: str = typer.Option(
        "markdown",
        "--output-format",
        "-f",
        help="Output format: markdown or txt",
    ),
    no_tables: bool = typer.Option(
        False,
        "--no-tables/--tables",
        help="Exclude tables from extraction (default includes tables)",
    ),
    include_comments: bool = typer.Option(
        False,
        "--include-comments/--no-comments",
        help="Include comments in extraction (default excludes)",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        help="Logging level: DEBUG, INFO, WARNING, ERROR",
    ),
) -> None:
    """Process a single HTML file."""
    setup_logging(log_level)

    try:
        format_normalized = format_output_format(output_format)
    except typer.BadParameter as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    logger = logging.getLogger(__name__)

    try:
        text = clean_html_file(
            input_file,
            output_format=format_normalized,
            include_tables=not no_tables,
            include_comments=include_comments,
        )

        if output is not None:
            # Write to exact path
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text, encoding="utf-8")
            logger.info(f"Wrote output to: {output}")
        else:
            # Write to output-dir with flat naming
            output_path_dir = output_dir or get_default_output_dir()
            out_path = write_output_text(
                text=text,
                output_format=format_normalized,
                input_dir=input_file.parent,
                output_dir=output_path_dir,
                input_file=input_file,
                overwrite=True,
                flat_output=True,
            )
            logger.info(f"Wrote output to: {out_path}")

        raise typer.Exit(0)

    except Exception as e:
        logger.error(f"Failed to process {input_file}: {e}", exc_info=True)
        raise typer.Exit(2)


@app.command()
def select(
    input_dir: Path = typer.Option(
        None,
        "--input-dir",
        "-i",
        help="Directory containing HTML files (default: ./data/html)",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    output_dir: Path = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Directory to write cleaned files (default: ./data/output)",
        file_okay=False,
        dir_okay=True,
    ),
    output_format: str = typer.Option(
        "markdown",
        "--output-format",
        "-f",
        help="Output format: markdown or txt",
    ),
    overwrite: bool = typer.Option(
        True,
        "--overwrite/--no-overwrite",
        help="Overwrite existing output files (default: overwrite)",
    ),
    no_tables: bool = typer.Option(
        False,
        "--no-tables/--tables",
        help="Exclude tables from extraction (default includes tables)",
    ),
    include_comments: bool = typer.Option(
        False,
        "--include-comments/--no-comments",
        help="Include comments in extraction (default excludes)",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        help="Logging level: DEBUG, INFO, WARNING, ERROR",
    ),
) -> None:
    """Interactively select HTML files to process using a checkbox UI."""
    setup_logging(log_level)

    input_path = input_dir or get_default_input_dir()
    output_path = output_dir or get_default_output_dir()

    try:
        format_normalized = format_output_format(output_format)
    except typer.BadParameter as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if not input_path.exists():
        console.print(f"[red]Error:[/red] Input directory does not exist: {input_path}")
        raise typer.Exit(1)

    logger = logging.getLogger(__name__)

    # Find all HTML files
    html_files = sorted(iter_html_files(input_path))
    if not html_files:
        console.print(f"[yellow]No HTML files found in: {input_path}[/yellow]")
        raise typer.Exit(0)

    # Build selection choices
    choices = [
        questionary.Choice(
            title=str(f.relative_to(input_path)),
            value=f,
            checked=False,
        )
        for f in html_files
    ]

    # Show interactive selector
    try:
        selected = questionary.checkbox(
            "Select HTML files to process:",
            choices=choices,
            instruction="(Use arrow keys to navigate, space to select, enter to confirm)",
        ).ask()

        if not selected:
            console.print("[yellow]No files selected. Exiting.[/yellow]")
            raise typer.Exit(0)

    except KeyboardInterrupt:
        console.print("\n[yellow]Selection cancelled.[/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        logger.error(f"Selection failed: {e}", exc_info=True)
        raise typer.Exit(2)

    logger.info(f"Processing {len(selected)} selected files")
    logger.info(f"Output directory: {output_path}")
    logger.info(f"Format: {format_normalized}, Overwrite: {overwrite}")

    try:
        results = run_batch(
            input_dir=input_path,
            output_dir=output_path,
            output_format=format_normalized,
            overwrite=overwrite,
            limit=None,
            include_tables=not no_tables,
            include_comments=include_comments,
            flat_output=True,
            input_files=selected,
        )

        ok = sum(1 for r in results if r.ok)
        failed = sum(1 for r in results if not r.ok)

        logger.info(f"Done. Processed: {len(results)}, Success: {ok}, Failed: {failed}")
        if failed > 0:
            logger.warning("Some files failed to process:")
            for r in results:
                if not r.ok:
                    logger.warning(f"  - {r.input_path}: {r.error}")

        raise typer.Exit(0 if failed == 0 else 1)

    except Exception as e:
        logger.error(f"Batch processing failed: {e}", exc_info=True)
        raise typer.Exit(2)


# Default command: run batch with cwd-relative defaults
@app.callback(invoke_without_command=True)
def default(
    ctx: typer.Context,
    input_dir: Path = typer.Option(
        None,
        "--input-dir",
        "-i",
        help="Directory containing HTML files (default: ./data/html)",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    output_dir: Path = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Directory to write cleaned files (default: ./data/output)",
        file_okay=False,
        dir_okay=True,
    ),
    output_format: str = typer.Option(
        "markdown",
        "--output-format",
        "-f",
        help="Output format: markdown or txt",
    ),
    overwrite: bool = typer.Option(
        True,
        "--overwrite/--no-overwrite",
        help="Overwrite existing output files (default: overwrite)",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-n",
        help="Process only the first N files (for quick tests)",
    ),
    no_tables: bool = typer.Option(
        False,
        "--no-tables/--tables",
        help="Exclude tables from extraction (default includes tables)",
    ),
    include_comments: bool = typer.Option(
        False,
        "--include-comments/--no-comments",
        help="Include comments in extraction (default excludes)",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        help="Logging level: DEBUG, INFO, WARNING, ERROR",
    ),
) -> None:
    """Clean HTML files into readable markdown/text using Trafilatura.

    If no subcommand is specified, runs batch processing with default settings.
    """
    # If a subcommand was invoked, don't run default behavior
    if ctx.invoked_subcommand is not None:
        return

    # Run batch processing with provided args
    setup_logging(log_level)

    input_path = input_dir or get_default_input_dir()
    output_path = output_dir or get_default_output_dir()

    try:
        format_normalized = format_output_format(output_format)
    except typer.BadParameter as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if not input_path.exists():
        console.print(f"[red]Error:[/red] Input directory does not exist: {input_path}")
        raise typer.Exit(1)

    logger = logging.getLogger(__name__)
    logger.info(f"Processing HTML files from: {input_path}")
    logger.info(f"Output directory: {output_path}")
    logger.info(f"Format: {format_normalized}, Overwrite: {overwrite}")

    try:
        results = run_batch(
            input_dir=input_path,
            output_dir=output_path,
            output_format=format_normalized,
            overwrite=overwrite,
            limit=limit,
            include_tables=not no_tables,
            include_comments=include_comments,
            flat_output=True,
        )

        ok = sum(1 for r in results if r.ok)
        failed = sum(1 for r in results if not r.ok)

        logger.info(f"Done. Processed: {len(results)}, Success: {ok}, Failed: {failed}")
        if failed > 0:
            logger.warning("Some files failed to process:")
            for r in results:
                if not r.ok:
                    logger.warning(f"  - {r.input_path}: {r.error}")

        raise typer.Exit(0 if failed == 0 else 1)

    except Exception as e:
        logger.error(f"Batch processing failed: {e}", exc_info=True)
        raise typer.Exit(2)


# Entry point for console script
def main() -> None:
    """Entry point for html-cleaner console script."""
    app()


if __name__ == "__main__":
    main()
