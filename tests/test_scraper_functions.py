import pytest
import json
from unittest.mock import patch, MagicMock
from trafilatura_scraper import scrape_article_with_trafilatura, slugify, format_article_markdown
import trafilatura

def test_slugify_function():
    """Test the slugify function with various inputs"""
    # Test normal text
    assert slugify("Hello World!") == "hello_world"
    assert slugify("This is a test article") == "this_is_a_test_article"

    # Test with special characters
    assert slugify("Hello, World! How are you?") == "hello_world_how_are_you"
    assert slugify("Article: The Future of AI") == "article_the_future_of_ai"

    # Test empty string
    assert slugify("") == "untitled"
    assert slugify(None) == "untitled"

    # Test long strings
    long_string = "a" * 150
    result = slugify(long_string)
    assert len(result) == 100  # Should be truncated to 100 chars

    # Test with multiple spaces
    assert slugify("Hello    World") == "hello_world"

def test_format_article_markdown():
    """Test the markdown formatting function"""
    test_data = {
        "title": "Test Article",
        "author": "John Doe",
        "date": "2023-01-01",
        "sitename": "Test News",
        "description": "This is a test description",
        "categories": ["Tech", "AI"],
        "tags": ["testing", "python"],
        "text": "This is the main content"
    }

    markdown = format_article_markdown(test_data, "This is the main content")

    # Check that all expected sections are present
    assert "# Test Article" in markdown
    assert "**Author:** John Doe" in markdown
    assert "**Published:** 2023-01-01" in markdown
    assert "**Source:** Test News" in markdown
    assert "## Summary" in markdown
    assert "This is a test description" in markdown
    assert "**Categories:** Tech, AI" in markdown
    assert "**Tags:** testing, python" in markdown
    assert "## Article Content" in markdown
    assert "This is the main content" in markdown

def test_format_article_markdown_missing_fields():
    """Test markdown formatting with missing fields"""
    test_data = {
        "title": "Minimal Article",
        "text": "Content only"
    }

    markdown = format_article_markdown(test_data, "Content only")

    assert "# Minimal Article" in markdown
    assert "## Article Content" in markdown
    assert "Content only" in markdown

@pytest.fixture
def mock_trafilatura():
    """Mock trafilatura functions for testing"""
    with patch('trafilatura.fetch_url') as mock_fetch, \
         patch('trafilatura.extract') as mock_extract:
        yield mock_fetch, mock_extract

def test_scrape_article_with_trafilatura_success(mock_trafilatura):
    """Test successful scraping scenario"""
    mock_fetch, mock_extract = mock_trafilatura

    # Mock successful responses
    mock_fetch.return_value = "<html>test content</html>"
    mock_extract.side_effect = [
        json.dumps({
            "title": "Test Article",
            "author": "Test Author",
            "date": "2023-01-01",
            "sitename": "Test Site",
            "hostname": "test.com",
            "description": "Test description",
            "categories": ["test"],
            "tags": ["tag1"],
            "fingerprint": "123",
            "language": "en",
            "text": "Test text content",
            "source": "test-source",
            "source-hostname": "test-hostname"
        }),
        "Plain text content"
    ]

    result_data, result_text = scrape_article_with_trafilatura("https://test.com/article")

    # Verify the result structure
    assert result_data is not None
    assert result_text == "Plain text content"

    # Check that all expected fields are present
    assert result_data["url"] == "https://test.com/article"
    assert result_data["title"] == "Test Article"
    assert result_data["author"] == "Test Author"
    assert result_data["sitename"] == "Test Site"
    assert result_data["text"] == "Test text content"
    assert result_data["raw_text"] == "Plain text content"

    # Check that timestamps are present
    assert "scraped_at" in result_data

@pytest.mark.slow
def test_scrape_article_with_trafilatura_failure(mock_trafilatura):
    """Test failed scraping scenario"""
    mock_fetch, mock_extract = mock_trafilatura

    # Mock failed download
    mock_fetch.return_value = None

    result_data, result_text = scrape_article_with_trafilatura("https://test.com/article")

    # Should return None for data and error message for text
    assert result_data is None
    assert result_text is not None
    assert "Both trafilatura and requests failed to download" in result_text

def test_scrape_article_with_trafilatura_extraction_failure(mock_trafilatura):
    """Test scenario where download succeeds but extraction fails"""
    mock_fetch, mock_extract = mock_trafilatura

    # Mock successful download but failed extraction
    mock_fetch.return_value = "<html>test content</html>"
    mock_extract.side_effect = [
        None,  # First call (JSON extraction) fails
        "Plain text content"
    ]

    result_data, result_text = scrape_article_with_trafilatura("https://test.com/article")

    # Should return None for data and error message for text
    assert result_data is None
    assert result_text is not None
    assert "Could not extract article content" in result_text

def test_scrape_article_with_trafilatura_json_parse_failure(mock_trafilatura):
    """Test scenario where JSON parsing fails"""
    mock_fetch, mock_extract = mock_trafilatura

    # Mock successful download and extraction but invalid JSON
    mock_fetch.return_value = "<html>test content</html>"
    mock_extract.side_effect = [
        "invalid json content",  # Invalid JSON
        "Plain text content"
    ]

    result_data, result_text = scrape_article_with_trafilatura("https://test.com/article")

    # Should return None for data and error message for text
    assert result_data is None
    assert result_text is not None
    assert "JSON parsing error" in result_text

def test_scrape_article_with_trafilatura_text_extraction_failure(mock_trafilatura):
    """Test scenario where JSON extraction succeeds but text extraction fails"""
    mock_fetch, mock_extract = mock_trafilatura

    # Mock successful JSON extraction but failed text extraction
    mock_fetch.return_value = "<html>test content</html>"
    mock_extract.side_effect = [
        json.dumps({
            "title": "Test Article",
            "text": "Test text content"
        }),
        Exception("Text extraction failed")  # Text extraction fails
    ]

    result_data, result_text = scrape_article_with_trafilatura("https://test.com/article")

    # Should return None for data and error message for text
    assert result_data is None
    assert result_text is not None
    assert "Text extraction error" in result_text

def test_scrape_article_with_trafilatura_requests_fallback():
    """Test the fallback to requests library when trafilatura fetch fails"""
    with patch('trafilatura.fetch_url') as mock_fetch, \
         patch('trafilatura.extract') as mock_extract, \
         patch('requests.get') as mock_requests:

        # Mock trafilatura fetch failure but requests success
        mock_fetch.return_value = None
        mock_requests.return_value = MagicMock()
        mock_requests.return_value.text = "<html>fallback content</html>"
        mock_requests.return_value.status_code = 200

        mock_extract.side_effect = [
            json.dumps({
                "title": "Fallback Article",
                "text": "Fallback text content"
            }),
            "Fallback plain text content"
        ]

        result_data, result_text = scrape_article_with_trafilatura("https://test.com/article")

        # Should succeed with fallback
        assert result_data is not None
        assert result_data["title"] == "Fallback Article"
        assert result_text == "Fallback plain text content"
        mock_requests.assert_called_once()