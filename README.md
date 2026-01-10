# scraper_cleaner

A comprehensive web scraping and content extraction toolkit with API support.

## Overview

The scraper_cleaner project is a Python-based web scraping solution that provides both command-line and API-based interfaces for extracting structured content from websites. It uses advanced libraries like Trafilatura for high-quality article extraction and BeautifulSoup for HTML parsing.

## Features

### 1. Core Scraping Functionality
- **Trafilatura-based extraction**: Uses the powerful Trafilatura library for extracting article content, metadata, and structured data
- **Multiple output formats**: Supports JSON, Markdown, and plain text outputs
- **Comprehensive metadata extraction**: Extracts titles, authors, dates, categories, tags, and more
- **Robust error handling**: Graceful handling of network issues, parsing errors, and edge cases

### 2. API Interface
- **FastAPI-based REST API**: Provides a modern, high-performance API for programmatic access
- **CORS support**: Configured for cross-origin requests
- **Structured responses**: Returns consistent JSON responses with success/failure indicators
- **Health monitoring**: Built-in health check endpoint

### 3. Command Line Tools
- **Interactive scraping**: Command-line interface for manual URL scraping
- **Batch processing**: Support for processing multiple URLs
- **Data organization**: Automatic file naming and directory structure

## Project Structure

```
scraper_cleaner/
├── api/
│   └── main.py          # FastAPI application with REST endpoints
├── artifacts/           # Documentation and status files
├── data/                # Output directory for scraped content
├── main.py              # Original scraping script (Scroll.in specific)
├── trafilatura_scraper.py # Core scraping library
├── pyproject.toml       # Project dependencies and configuration
├── README.md            # This documentation
└── .gitignore           # Git ignore rules
```

## Components

### 1. `trafilatura_scraper.py` - Core Scraping Engine

The main scraping module that provides:

- `scrape_article_with_trafilatura(url)`: Extracts structured article data and clean text
- `slugify(text)`: Converts text to URL-friendly slugs
- `format_article_markdown(data, text)`: Formats article data as Markdown
- `setup_logging()`: Configures logging for the application

### 2. `api/main.py` - REST API Interface

FastAPI application providing:

- **GET `/`**: Root endpoint with service information
- **GET `/health`**: Health check endpoint
- **POST `/scrape`**: Scrape articles from URLs with configurable options

### 3. `main.py` - Original Scraping Script

Specialized scraper for Scroll.in website with:

- HTML parsing using BeautifulSoup
- Structured data extraction
- Content cleaning and formatting
- Multiple output formats (JSON, Markdown, HTML)

## Installation

```bash
# Clone the repository
git clone https://github.com/your-repo/scraper_cleaner.git
cd scraper_cleaner

# Install dependencies
uv pip install
```

### Global CLI Installation (Recommended)

Install `html-cleaner` as a global command using `pipx`:

```bash
# Install globally (WSL/Linux)
pipx install -e /path/to/scraper_cleaner

# Or if you're in the repo directory
pipx install -e .

# Verify installation
html-cleaner --help
```

**Note**: Ensure `~/.local/bin` is on your PATH. `pipx` typically handles this automatically, but you may need to add it manually:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

For more details, see [artifacts/html_cleaner_docs.md](artifacts/html_cleaner_docs.md).

## Usage

### HTML Cleaner CLI (`html-cleaner`)

The `html-cleaner` command provides a modern CLI for cleaning local HTML files:

```bash
# Default: batch process ./data/html -> ./data/output
html-cleaner

# Batch process with custom directories
html-cleaner --input-dir /path/to/html --output-dir /path/to/output

# Interactive file selector
html-cleaner select

# Process a single file
html-cleaner file input.html --output output.md

# Batch subcommand with options
html-cleaner batch --output-format txt --limit 10 --no-overwrite
```

**Commands:**
- `html-cleaner` (no args): Batch process with cwd-relative defaults
- `html-cleaner batch`: Batch process a directory of HTML files
- `html-cleaner file INPUT.html`: Process a single HTML file
- `html-cleaner select`: Interactive multi-select from input directory

**Key Features:**
- Flat output directory layout (collision-safe hash-based naming)
- Overwrite by default (use `--no-overwrite` to skip existing files)
- CWD-relative defaults (works from any directory)
- Interactive file selection with checkbox UI

For detailed usage, see [artifacts/html_cleaner_docs.md](artifacts/html_cleaner_docs.md).

### Legacy Script (Backwards Compatible)

```bash
# Legacy script interface (still supported)
python scripts/html_cleaner.py

# Run the main scraper (interactive)
python trafilatura_scraper.py

# Run the Scroll.in specific scraper
python main.py
```

### API Server

```bash
# Start the API server
python api/main.py

# The API will be available at http://localhost:8001
```

### API Endpoints

**POST `/scrape`**
```json
{
  "url": "https://example.com/article",
  "include_raw_text": true,
  "include_metadata": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "url": "https://example.com/article",
    "title": "Article Title",
    "author": "Author Name",
    "date": "2023-01-01",
    "text": "Article content...",
    "raw_text": "Raw article text...",
    "metadata": {...}
  },
  "error": null
}
```

### cURL Usage Examples

**Basic Scraping Request:**
```bash
curl -X POST "http://localhost:8001/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/article",
    "include_raw_text": true,
    "include_metadata": true
  }'
```

**Batch Scraping Request:**
```bash
curl -X POST "http://localhost:8001/batch-scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://example.com/article1",
      "https://example.com/article2"
    ],
    "include_raw_text": true,
    "include_metadata": true
  }'
```

**Authentication and Token Usage:**
```bash
# Get authentication token
curl -X POST "http://localhost:8001/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpassword"

# Use token for authenticated requests
curl -X POST "http://localhost:8001/scrape" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "url": "https://example.com/article",
    "include_raw_text": true,
    "include_metadata": true
  }'
```

**Health Check:**
```bash
curl -X GET "http://localhost:8001/health"
```

**Root Endpoint:**
```bash
curl -X GET "http://localhost:8001/"
```

## Dependencies

- Python 3.12+
- Trafilatura 2.0.0+
- FastAPI 0.111.0+
- Uvicorn 0.30.1+
- Requests 2.32.5+
- BeautifulSoup 4.14.3+

## Recent Fixes

- **Type Safety**: Fixed null reference issues in `api/main.py` where `spec` could be `None`
- **Error Handling**: Added proper null checks for module loading
- **Code Quality**: Improved type annotations and error messages

## Development

```bash
# Run tests (parallel execution by default)
.venv/bin/pytest tests/

# Run with hot reload (development)
uvicorn api.main:app --reload --port 8001
```

## Testing with pytest-xdist

The project now includes pytest-xdist for parallel test execution, significantly improving test suite performance.

### Parallel Test Execution

By default, tests run in parallel using auto-detected CPU cores (10 workers in this environment):

```bash
# Run all tests in parallel (default behavior)
.venv/bin/pytest tests/

# Run specific number of workers
.venv/bin/pytest tests/ -n 4

# Run tests sequentially (if needed)
.venv/bin/pytest tests/ -n 0
```

### Slow Test Management

Slow tests are automatically excluded from parallel runs by default:

```bash
# Run only fast tests (default)
.venv/bin/pytest tests/ -m "not slow"

# Run slow tests separately
.venv/bin/pytest tests/ -m slow

# Run all tests including slow ones
.venv/bin/pytest tests/ -m ""
```

### Performance Results

- **Before optimization**: ~60 seconds for full test suite
- **After parallel execution**: ~11 seconds for fast tests (26 tests)
- **Slow tests**: ~11 seconds for 5 slow tests
- **Total improvement**: ~80% reduction in test execution time

### Test Execution Examples

```bash
# Quick development feedback (fast tests only, parallel)
.venv/bin/pytest tests/ -m "not slow"

# Full test suite (parallel)
.venv/bin/pytest tests/ -m ""

# Specific test file
.venv/bin/pytest tests/test_api_integration.py

# With verbose output
.venv/bin/pytest tests/ -v

# Show test durations
.venv/bin/pytest tests/ --durations=10
```

### Configuration

The pytest configuration is defined in `pytest.ini`:

```ini
[pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks integration tests
    unit: marks unit tests

# pytest-xdist configuration for parallel execution
addopts = -n auto -m "not slow"
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

### Best Practices

1. **Test Isolation**: All tests are designed to be parallel-safe with proper mocking and fixtures
2. **Slow Test Marking**: Use `@pytest.mark.slow` decorator for tests that take >1 second
3. **Resource Management**: Tests avoid shared state and use fixtures for setup/teardown
4. **Mocking**: External dependencies are properly mocked to ensure fast, reliable tests

## License

MIT License
