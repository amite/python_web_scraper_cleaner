from fastmcp import FastMCP
import pathlib
import json
from typing import List
import os
import requests

# Initialize FastMCP
mcp = FastMCP("News-Archive")


# Constants
DATA_DIR = pathlib.Path(__file__).parent.parent / "data" / "news_output"

def get_markdown_files() -> List[pathlib.Path]:
    """Helper to get all markdown files."""
    if not DATA_DIR.exists():
        return []
    return list(DATA_DIR.glob("*.md"))

# --- Logic Functions ---

def _list_news_logic() -> str:
    files = get_markdown_files()
    return "\n".join([f.name for f in files])

def _get_article_logic(filename: str) -> str:
    file_path = DATA_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Article not found: {filename}")
    
    # Security check to prevent directory traversal
    try:
        file_path.relative_to(DATA_DIR)
    except ValueError:
         raise ValueError(f"Access denied: {filename}")

    return file_path.read_text(encoding="utf-8")

def _search_news_logic(query: str) -> str:
    results = []
    query_lower = query.lower()
    
    for file_path in get_markdown_files():
        try:
            content = file_path.read_text(encoding="utf-8")
            if query_lower in content.lower():
                # Find the index of the match for a snippet
                idx = content.lower().find(query_lower)
                start = max(0, idx - 50)
                end = min(len(content), idx + 150)
                snippet = content[start:end].replace("\n", " ")
                results.append(f"- **{file_path.name}**: ...{snippet}...")
        except Exception:
            continue
            
    if not results:
        return f"No matches found for '{query}'."
        
    return "\n".join(results)

def _get_latest_news_logic(limit: int = 5) -> str:
    files = get_markdown_files()
    # Sort by modification time, newest first
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    recent_files = files[:limit]
    results = []
    
    for f in recent_files:
        try:
            content = f.read_text(encoding="utf-8")
            summary = content[:100].replace("\n", " ")
            results.append(f"- **{f.name}**: {summary}...")
        except Exception:
            continue
            
    return "\n".join(results)

def _find_best_article(query: str) -> pathlib.Path | None:
    """Find the most relevant article for a query."""
    best_file = None
    max_score = 0
    query_lower = query.lower()
    
    import string
    
    # Basic stop words to ignore
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", 
                  "of", "with", "is", "are", "was", "were", "be", "this", "that", "it", 
                  "what", "which", "who", "when", "where", "why", "how", "latest", "news", 
                  "question", "from", "by", "as"}
    
    # Clean and split query
    translator = str.maketrans('', '', string.punctuation)
    query_clean = query_lower.translate(translator)
    query_terms = [term for term in query_clean.split() if term not in stop_words]
    
    if not query_terms:
         # If all words were stop words, fall back to original query terms
         query_terms = query_clean.split()

    for file_path in get_markdown_files():
        try:
            content = file_path.read_text(encoding="utf-8").lower()
            score = 0
            # Simple scoring: count occurences of meaningful query terms
            for term in query_terms:
                score += content.count(term)
            
            if score > max_score:
                max_score = score
                best_file = file_path
        except Exception:
            continue
            
    return best_file

def _query_ollama(prompt: str, model: str = "gemma3:12b-it-qat") -> str:
    """Query the Ollama API."""
    url = "http://localhost:11434/api/generate"
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json().get("response", "Error: No response from model.")
    except Exception as e:
        return f"Error communicating with Ollama: {e}"

def _query_ollama_stream(prompt: str, model: str = "gemma3:12b-it-qat"):
    """Query the Ollama API with streaming enabled. Yields tokens as they arrive."""
    url = "http://localhost:11434/api/generate"
    data = {
        "model": model,
        "prompt": prompt,
        "stream": True
    }
    try:
        response = requests.post(url, json=data, stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    if "response" in chunk:
                        yield chunk["response"]
                    if chunk.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        yield f"Error communicating with Ollama: {e}"

def _ask_news_logic(question: str) -> str:
    article_path = _find_best_article(question)
    if not article_path:
        return "I couldn't find any relevant news articles to answer your question."
    
    try:
        content = article_path.read_text(encoding="utf-8")
        # Keep context within reasonable limits for the model
        if len(content) > 10000:
             content = content[:10000] + "...(truncated)"
             
        prompt = f"""You are a helpful news assistant. Use the provided article to answer the user's question clearly and concisely.
        
Article Content ({article_path.name}):
{content}

Question:
{question}
"""
        return _query_ollama(prompt)
    except Exception as e:
        return f"Error processing article: {e}"

def _ask_news_logic_stream(question: str):
    """Streaming version of _ask_news_logic. Yields tokens as they arrive."""
    article_path = _find_best_article(question)
    if not article_path:
        yield "I couldn't find any relevant news articles to answer your question."
        return
    
    try:
        content = article_path.read_text(encoding="utf-8")
        # Keep context within reasonable limits for the model
        if len(content) > 10000:
             content = content[:10000] + "...(truncated)"
             
        prompt = f"""You are a helpful news assistant. Use the provided article to answer the user's question clearly and concisely.
        
Article Content ({article_path.name}):
{content}

Question:
{question}
"""
        for token in _query_ollama_stream(prompt):
            yield token
    except Exception as e:
        yield f"Error processing article: {e}"

# --- MCP Resources & Tools ---

@mcp.resource("news://list")
def list_news() -> str:
    """List all available news article filenames."""
    return _list_news_logic()

@mcp.resource("news://article/{filename}")
def get_article(filename: str) -> str:
    """Read the content of a specific news article.
    
    Args:
        filename: The name of the file to read (must end in .md)
    """
    return _get_article_logic(filename)

@mcp.tool()
def search_news(query: str) -> str:
    """Search for a keyword in all news articles.
    
    Args:
        query: The keyword to search for (case-insensitive).
        
    Returns:
        A formatted string with matching filenames and context snippets.
    """
    return _search_news_logic(query)

@mcp.tool()
def get_latest_news(limit: int = 5) -> str:
    """Get the most recent news articles based on file creation time.
    
    Args:
        limit: The number of articles to return (default: 5).
        
    Returns:
        A list of the most recent articles with a brief summary (first 100 chars).
    """
    return _get_latest_news_logic(limit)

@mcp.tool()
def ask_news(question: str) -> str:
    """Answers a question about the news by automatically finding and reading the most relevant article.
    
    Use this tool for general Q&A. It is smarter than `search_news` because it combines search and reading into one step to give a direct answer.
    
    Args:
        question: The question to ask.
        
    Returns:
        An answer generated by the AI based on the most relevant news article.
    """
    return _ask_news_logic(question)

if __name__ == "__main__":
    mcp.run()

