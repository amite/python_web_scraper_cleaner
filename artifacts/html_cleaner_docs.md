# HTML Cleaner CLI - Implementation Summary & Usage Guide

## Overview

The `html-cleaner` command is a global CLI tool that cleans local HTML files into readable markdown or text using Trafilatura. It supports batch processing, single-file processing, and interactive file selection with a modern Typer-based interface.

## Implementation Summary

### Architecture

The implementation follows a clean separation of concerns:

```
scraper_cleaner/
├── __init__.py                  # Package initialization
├── html_cleaner_core.py         # Core functionality (extraction logic)
└── cli/
    ├── __init__.py
    └── html_cleaner.py          # Typer CLI application
```

**Key Design Decisions:**

1. **Package Structure**: Core logic extracted from `scripts/html_cleaner.py` into `scraper_cleaner/html_cleaner_core.py` for reusability
2. **CLI Framework**: Uses Typer for type-safe CLI with automatic help generation
3. **Interactive Selection**: Uses Questionary for checkbox-based multi-select UI
4. **Output Format**: Flat directory layout with hash-based collision-safe naming
5. **Defaults**: CWD-relative defaults (`./data/html` -> `./data/output`) for portability

### Core Features

#### 1. Flat Output Naming
- **Purpose**: Prevent file collisions when processing files from nested directories
- **Implementation**: Converts relative paths to flat filenames with hash suffix
- **Example**: `news/article.html` → `news__article__3f2a9c1d.md`
- **Deterministic**: Same input path always produces same hash (for reproducibility)

#### 2. Overwrite Behavior
- **Default**: Overwrite existing files (new behavior per design requirements)
- **Option**: `--no-overwrite` flag to skip existing non-empty files
- **Legacy Support**: `scripts/html_cleaner.py` maintains old behavior (skip by default)

#### 3. CWD-Relative Defaults
- Input: `./data/html` (relative to current working directory)
- Output: `./data/output` (relative to current working directory)
- **Benefit**: Works from any directory without needing absolute paths

#### 4. Interactive File Selection
- **UI**: Checkbox-based multi-select using Questionary
- **Scope**: Recursively finds all `.html` and `.htm` files in input directory
- **User Experience**: Navigate with arrow keys, select with space, confirm with enter

### Package Configuration

The tool is configured in `pyproject.toml`:

```toml
[project.scripts]
html-cleaner = "scraper_cleaner.cli.html_cleaner:app"
```

**Build System**: Uses `hatchling` (PEP 517 compliant)

**Dependencies**:
- `typer>=0.21.1` - CLI framework
- `questionary>=2.1.1` - Interactive prompts
- `rich>=14.2.0` - Rich terminal output and logging
- `trafilatura>=2.0.0` - HTML extraction engine

## Installation

### Prerequisites

- Python 3.12+
- `pipx` (recommended) or `pip` with `--user` flag
- `uv` (for development)

### Global Installation with pipx (Recommended)

```bash
# Navigate to the project directory
cd /path/to/scraper_cleaner

# Install globally using pipx
pipx install -e .

# Verify installation
html-cleaner --help

# Ensure ~/.local/bin is on PATH (pipx typically handles this)
export PATH="$HOME/.local/bin:$PATH"  # Add to ~/.bashrc or ~/.zshrc for persistence
```

### Development Installation

```bash
# Install in editable mode for development
uv pip install -e .

# Or using pip
pip install -e .
```

**Note**: Editable installs allow code changes to take effect without reinstalling.

## Usage Guide

### Basic Usage

#### Default Command (Batch Processing)

```bash
# Process all HTML files in ./data/html, output to ./data/output
html-cleaner

# With custom directories
html-cleaner --input-dir /path/to/html --output-dir /path/to/output

# Change output format
html-cleaner --output-format txt

# Process only first 10 files (for quick tests)
html-cleaner --limit 10

# Skip existing files (don't overwrite)
html-cleaner --no-overwrite
```

#### Batch Subcommand (Explicit)

```bash
# Explicit batch command with all options
html-cleaner batch \
  --input-dir ./data/html \
  --output-dir ./data/output \
  --output-format markdown \
  --overwrite \
  --limit 5 \
  --no-tables \
  --include-comments \
  --log-level DEBUG
```

**Options:**
- `--input-dir, -i`: Input directory (default: `./data/html`)
- `--output-dir, -o`: Output directory (default: `./data/output`)
- `--output-format, -f`: Output format: `markdown` or `txt` (default: `markdown`)
- `--overwrite/--no-overwrite`: Overwrite existing files (default: `--overwrite`)
- `--limit, -n`: Process only first N files
- `--no-tables/--tables`: Exclude/include tables (default: include)
- `--include-comments/--no-comments`: Include/exclude comments (default: exclude)
- `--log-level`: Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`)

#### Single File Processing

```bash
# Process single file, output to specified path
html-cleaner file input.html --output output.md

# Process single file, output to default directory with flat naming
html-cleaner file article.html --output-dir ./cleaned

# With format options
html-cleaner file input.html --output output.txt --output-format txt --no-tables
```

**Arguments:**
- `INPUT_FILE`: Path to HTML file (required)
- `--output`: Exact output file path (optional; if not provided, uses `--output-dir` with flat naming)
- `--output-dir, -o`: Output directory if `--output` not specified (default: `./data/output`)
- All batch options apply: `--output-format`, `--no-tables`, `--include-comments`, etc.

#### Interactive File Selection

```bash
# Interactive selector from default input directory
html-cleaner select

# Interactive selector from custom directory
html-cleaner select --input-dir /path/to/html --output-dir /path/to/output

# With format options
html-cleaner select --output-format txt --no-overwrite
```

**How it works:**
1. Recursively finds all `.html` and `.htm` files in input directory
2. Displays checkbox list showing relative paths
3. User selects files with arrow keys (navigate) and space (select/deselect)
4. Press Enter to confirm selection
5. Processes selected files with same options as batch command

**Keyboard Controls:**
- `↑/↓`: Navigate through files
- `Space`: Select/deselect file
- `a`: Select all
- `d`: Deselect all
- `Enter`: Confirm selection and process
- `Ctrl+C`: Cancel

### Output Structure

#### Flat Output Mode (Default)

Files are written to a flat directory structure with hash-based naming:

```
output_dir/
├── manifest.json
├── news__article__3f2a9c1d.md
├── blog__post__7e8f9a2b.md
└── docs__guide__1c2d3e4f.txt
```

**Naming Convention:**
- Replace directory separators with double underscore (`__`)
- Remove extension from base name
- Append 8-character MD5 hash of relative path
- Add appropriate extension (`.md` or `.txt`)

**Benefits:**
- No nested directories (easier to browse)
- Collision-safe (hash prevents name conflicts)
- Deterministic (same input produces same output name)

#### Manifest File

Every batch operation generates a `manifest.json` in the output directory:

```json
{
  "generated_at": "2026-01-10T12:34:56.789012",
  "input_dir": "/path/to/html",
  "output_dir": "/path/to/output",
  "total": 10,
  "ok": 8,
  "failed": 2,
  "results": [
    {
      "input_path": "/path/to/html/news/article.html",
      "output_path": "/path/to/output/news__article__3f2a9c1d.md",
      "ok": true,
      "extracted_chars": 1234,
      "error": null
    },
    {
      "input_path": "/path/to/html/error.html",
      "output_path": null,
      "ok": false,
      "extracted_chars": 0,
      "error": "Trafilatura could not extract main text (empty result)."
    }
  ]
}
```

**Use Cases:**
- Audit processing results
- Track which files succeeded/failed
- Reproduce processing runs
- Debug extraction issues

### Advanced Usage

#### Processing Specific Files

```bash
# Process specific files using select command
html-cleaner select --input-dir /path/to/html

# Or use file command multiple times (not recommended for many files)
html-cleaner file file1.html && html-cleaner file file2.html
```

#### Format Options

```bash
# Markdown output (default, preserves structure)
html-cleaner --output-format markdown

# Plain text output (simpler, less structure)
html-cleaner --output-format txt

# Exclude tables from extraction
html-cleaner --no-tables

# Include HTML comments (usually not desired)
html-cleaner --include-comments
```

#### Logging

```bash
# Debug mode (verbose output)
html-cleaner --log-level DEBUG

# Quiet mode (errors only)
html-cleaner --log-level ERROR

# Info mode (default, shows progress)
html-cleaner --log-level INFO
```

#### Combining Options

```bash
# Real-world example: Process subset of files, txt format, skip tables
html-cleaner batch \
  --input-dir ./articles \
  --output-dir ./cleaned \
  --output-format txt \
  --limit 20 \
  --no-tables \
  --no-overwrite \
  --log-level INFO
```

## Examples

### Example 1: Basic Batch Processing

```bash
# Setup: HTML files in ~/Downloads/html
mkdir -p ~/Downloads/cleaned

# Process all HTML files
html-cleaner \
  --input-dir ~/Downloads/html \
  --output-dir ~/Downloads/cleaned

# Result: All HTML files cleaned to markdown in ~/Downloads/cleaned/
```

### Example 2: Interactive Selection

```bash
# Select specific files to process
html-cleaner select \
  --input-dir ~/Documents/articles \
  --output-dir ~/Documents/cleaned \
  --output-format txt

# User selects files via checkbox UI
# Only selected files are processed
```

### Example 3: Single File Processing

```bash
# Clean a single downloaded article
html-cleaner file ~/Downloads/article.html \
  --output ~/Documents/cleaned_article.md \
  --output-format markdown
```

### Example 4: Quick Test Run

```bash
# Process first 5 files to test
html-cleaner --limit 5 --log-level DEBUG

# Verify output
ls -lh ./data/output/
cat ./data/output/manifest.json | jq '.ok, .failed'
```

## Backwards Compatibility

The original `scripts/html_cleaner.py` script remains available for backwards compatibility:

```bash
# Legacy script interface (still works)
python scripts/html_cleaner.py --input-dir ./data/html --output-dir ./data/output

# Note: Legacy script uses directory-preserving output (not flat)
#       and defaults to --no-overwrite behavior
```

**Key Differences:**
- Legacy script preserves directory structure (not flat output)
- Legacy script defaults to `--no-overwrite` (skips existing files)
- Legacy script uses repo-relative defaults (not cwd-relative)

## Troubleshooting

### Command Not Found

```bash
# Verify installation
pipx list | grep html-cleaner

# Check PATH
echo $PATH | grep -q "$HOME/.local/bin" || echo "Not in PATH"

# Reinstall if needed
pipx reinstall html-cleaner --python python3.12
```

### Permission Errors

```bash
# Ensure output directory is writable
chmod +w /path/to/output

# Or use a directory you own
html-cleaner --output-dir ~/output
```

### Empty Extraction Errors

Some HTML files may not contain extractable content:

```bash
# Check manifest for failed files
cat ./data/output/manifest.json | jq '.results[] | select(.ok == false)'

# Process with debug logging
html-cleaner --log-level DEBUG 2>&1 | grep -i error
```

### Large File Sets

For processing many files:

```bash
# Process in batches using limit
html-cleaner --limit 100

# Use interactive selection for curation
html-cleaner select
```

## Development

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_html_cleaner.py

# Run with coverage
pytest --cov=scraper_cleaner tests/
```

### Code Structure

- **Core Logic**: `scraper_cleaner/html_cleaner_core.py`
  - Pure functions for extraction and file I/O
  - No CLI dependencies
  - Easily testable

- **CLI Interface**: `scraper_cleaner/cli/html_cleaner.py`
  - Typer application
  - Command definitions
  - User interaction handling

- **Legacy Script**: `scripts/html_cleaner.py`
  - Thin wrapper for backwards compatibility
  - Delegates to core logic

## Summary

The `html-cleaner` CLI provides a modern, user-friendly interface for cleaning HTML files with:

- **Global installation** via pipx
- **Multiple workflows**: batch, single-file, interactive selection
- **Flat output** with collision-safe naming
- **CWD-relative defaults** for portability
- **Rich terminal output** with progress and error reporting
- **Manifest generation** for auditability

For more information, see the main [README.md](../README.md) or run `html-cleaner --help`.
