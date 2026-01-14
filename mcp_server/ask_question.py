#!/usr/bin/env python3
"""
Simple command-line interface to ask questions about news articles.
Bypasses mcp-cli to directly use the working logic.
"""
# ask_question.py
from news_server import _ask_news_logic
import sys
if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What are danish officials saying?"
    print(_ask_news_logic(question))
