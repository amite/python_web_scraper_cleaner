from news_server import _list_news_logic, _get_article_logic, _search_news_logic, _get_latest_news_logic
import pathlib

def test_list_news():
    print("Testing news://list resource...")
    result = _list_news_logic()
    print(f"Result (first 100 chars): {result[:100]}...")
    assert len(result) > 0, "List should not be empty"

def test_get_article():
    print("\nTesting news://article/{filename} resource...")
    # Get first available file
    files = _list_news_logic().split("\n")
    if not files:
        print("No files to test")
        return
    
    filename = files[0]
    print(f"Reading {filename}...")
    content = _get_article_logic(filename)
    print(f"Content length: {len(content)}")
    assert len(content) > 0, "Content should not be empty"

def test_search_news():
    print("\nTesting search_news tool...")
    query = "the" # Common word
    result = _search_news_logic(query)
    print(f"Search results for '{query}':")
    print(result[:200] + "...")
    assert "No matches found" not in result, "Should find matches for 'the'"

def test_get_latest_news():
    print("\nTesting get_latest_news tool...")
    result = _get_latest_news_logic(limit=3)
    print(f"Latest news:\n{result}")
    assert len(result) > 0, "Latest news should not be empty"

if __name__ == "__main__":
    test_list_news()
    test_get_article()
    test_search_news()
    test_get_latest_news()
    print("\nAll tests passed!")

