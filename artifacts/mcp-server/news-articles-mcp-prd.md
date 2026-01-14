This is a concise Product Requirements Document (PRD).It provides the technical context of your existing project and clear instructions for building the server using modern 2026 standards.

---

# PRD: Local News Archive MCP Server

## 1. Overview

**Project Goal:** Build a Python-based Model Context Protocol (MCP) server that exposes a local directory of cleaned news articles (Markdown/JSON) to external AI clients.
**Primary Client:** `mcp-cli` using local **Ollama (gemma3:12b-it-qat)**. MCP CLI us here: https://github.com/chrishayuk/mcp-cli/blob/main/README.md for details.
**Data Source:** Local folder at `./data/output/` containing news articles in Markdown and structured JSON.

---

## 2. Technical Stack

* **Language:** Python 3.12+
* **Framework:** `fastmcp` (Official SDK-based high-level framework). Client will be https://github.com/chrishayuk/mcp-cli
* **Dependency Manager:** `uv` (standard for 2026).
* **Transport:** `stdio` (for local CLI/Ollama communication).

---

## 3. Data Schema & Requirements

The server must interface with the following file patterns in `data/news_output/`:

* **Markdown (.md):** Cleaned article content.

---

## 4. Functional Requirements (MCP Interface)

### A. Resources

Expose the archive as a virtual filesystem for the LLM.

1. **`news://list`**: Returns a list of all article filenames available in the directory.
2. **`news://article/{filename}`**: Returns the full text content of a specific Markdown article.

### B. Tools

Enable the LLM to perform active logic over the data.

1. **`search_news(query: str)`**:
* Perform a keyword search across all `.md` files.
* Return a list of matches with file names and a 200-character context snippet.


2. **`get_latest_news(limit: int = 5)`**:
* Parse timestamps from filenames or file creation dates.
* Return the names and summaries of the  most recent articles.


<!-- 3. **`summarize_archive()`**:
* Aggregate titles from the `manifest.json` (if present) or file list to provide a high-level table of contents. -->



---

## 5. Non-Functional Requirements

* **Performance:** Search should be optimized (caching file list in memory on startup).
* **Error Handling:** Graceful handling of missing files or invalid filenames.
* **Documentation:** Every tool and resource must have a clear Python docstring (MCP uses these as the "system instructions" for the LLM).

---

## 6. Implementation Instructions (For Claude)

1. Initialize a `FastMCP("News-Archive")` instance.
2. Implement `pathlib` for robust file handling in the `./data/output/` directory.
3. Ensure the `search_news` tool is case-insensitive.
4. Provide a `main` block that calls `mcp.run()`.
5. **Output:** Provide a single file `news_server.py` and a `pyproject.toml` compatible with `uv`.

---