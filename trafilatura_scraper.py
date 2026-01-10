"""
Compatibility shim.

The project implementation lives in `scripts/trafilatura_scraper.py`, but other
code (and tests) import `trafilatura_scraper` from the repository root.

This module loads the implementation by file path and re-exports its public API.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_impl() -> ModuleType:
    impl_path = Path(__file__).resolve().parent / "scripts" / "trafilatura_scraper.py"
    spec = importlib.util.spec_from_file_location("_trafilatura_scraper_impl", impl_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load trafilatura scraper implementation from {impl_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_impl = _load_impl()

scrape_article_with_trafilatura = _impl.scrape_article_with_trafilatura
slugify = _impl.slugify
format_article_markdown = _impl.format_article_markdown
setup_logging = _impl.setup_logging

__all__ = [
    "scrape_article_with_trafilatura",
    "slugify",
    "format_article_markdown",
    "setup_logging",
]

