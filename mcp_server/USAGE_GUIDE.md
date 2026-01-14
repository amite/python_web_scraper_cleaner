# News MCP Server Usage Guide

This generic Model Context Protocol (MCP) server exposes a local directory of markdown news articles to AI clients.

## Prerequisites

*   **Python**: 3.12 or higher
*   **uv**: Python package and project manager (recommended)
*   **Ollama**: Required for Q&A feature (must be running `gemma3:12b-it-qat`)
*   **mcp-cli** (optional): For testing from the command line

## Installation

1.  Navigate to the server directory:
    ```bash
    cd mcp_server
    ```

2.  Install dependencies:
    ```bash
    uv sync
    ```

## Running the Server

To start the server using stdio transport (standard input/output):

```bash
uv run news_server.py
```

## Connecting with Clients

### Using with `mcp-cli` & Ollama

This project was designed to work with `mcp-cli`. `mcp-cli` requires a configuration file to know how to start the server.

1.  Create a `server_config.json` file in your directory:
    ```json
    {
      "mcpServers": {
        "news": {
          "command": "uv",
          "args": ["run", "news_server.py"]
        }
      }
    }
    ```

2.  Run the client (specifying the available model):
    ```bash
    uvx mcp-cli --model gemma3:12b-it-qat
    ```
    (It will automatically load `server_config.json` from the current directory)

    Alternatively, specify the config file explicitly:
    ```bash
    uvx mcp-cli --config-file server_config.json --model gemma3:12b-it-qat
    ```

### Using with Claude Desktop

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "news-archive": {
      "command": "uv",
      "args": [
        "run",
        "/absolute/path/to/scraper_cleaner/mcp_server/news_server.py"
      ],
      "cwd": "/absolute/path/to/scraper_cleaner/mcp_server"
    }
  }
}
```

## Available Capabilities

### Resources (Data Access)

*   **`news://list`**
    *   Lists all available news article filenames in the archive.
*   **`news://article/{filename}`**
    *   Reads the full content of a specific markdown file.
    *   Example: `news://article/some_article.md`

### Tools (Functions)

*   **`search_news(query: str)`**
    *   Performs a case-insensitive keyword search across all articles.
    *   Returns matching filenames with 200-character context snippets.
*   **`get_latest_news(limit: int = 5)`**
    *   Returns the most recent articles based on file modification time.
    *   Default limit is 5.
*   **`ask_news(question: str)`**
    *   Asks a question about the news.
    *   Finds the most relevant article and uses `gemma3:12b-it-qat` to generate an answer.
    *   Example: `ask_news("What is the latest news from Iran?")`
