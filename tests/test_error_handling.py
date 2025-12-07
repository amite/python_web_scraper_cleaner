import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from api.main import app
import trafilatura_scraper

# Create test client
client = TestClient(app)

def test_scraper_error_handling():
    """Test error handling in the scraper functions"""
    # Test with invalid URL
    result_data, result_text = trafilatura_scraper.scrape_article_with_trafilatura("invalid-url")
    assert result_data is None
    assert result_text is not None
    assert "error" in result_text.lower() or "failed" in result_text.lower()

    # Test with empty URL
    result_data, result_text = trafilatura_scraper.scrape_article_with_trafilatura("")
    assert result_data is None
    assert result_text is not None

@pytest.mark.slow
def test_api_error_scenarios():
    """Test various error scenarios in the API"""
    # Test with malformed URL
    response = client.post("/scrape", json={"url": "not-a-valid-url"})
    assert response.status_code in [400, 500]  # Either bad request or internal error

    # Test with empty URL
    response = client.post("/scrape", json={"url": ""})
    assert response.status_code in [400, 500]

def test_api_request_validation():
    """Test request validation in the API"""
    # Test missing required fields
    response = client.post("/scrape", json={})
    assert response.status_code == 422  # Unprocessable Entity

    # Test invalid data types
    response = client.post("/scrape", json={"url": 123})  # URL should be string
    assert response.status_code == 422

def test_api_exception_handling():
    """Test that the API handles exceptions gracefully"""
    with patch('api.main.trafilatura_scraper.scrape_article_with_trafilatura') as mock_scrape:
        # Mock an exception
        mock_scrape.side_effect = Exception("Test exception")

        response = client.post("/scrape", json={"url": "https://test.com"})
        assert response.status_code == 500
        assert "Error scraping URL" in response.json()["detail"]

def test_api_logging():
    """Test that API operations are properly logged"""
    with patch('api.main.logging') as mock_logging:
        # Test successful request
        with patch('api.main.trafilatura_scraper.scrape_article_with_trafilatura') as mock_scrape:
            mock_scrape.return_value = (
                {"url": "https://test.com", "title": "Test"},
                "Test content"
            )

            response = client.post("/scrape", json={"url": "https://test.com"})
            assert response.status_code == 200

            # Check that logging was called
            mock_logging.info.assert_called()
            mock_logging.error.assert_not_called()

        # Test failed request
        with patch('api.main.trafilatura_scraper.scrape_article_with_trafilatura') as mock_scrape:
            mock_scrape.return_value = (None, "Test error")

            response = client.post("/scrape", json={"url": "https://test.com"})
            assert response.status_code == 400

            # Check that error logging was called
            mock_logging.error.assert_called()

def test_scraper_edge_cases():
    """Test edge cases in scraper functions"""
    # Test slugify with various edge cases
    assert trafilatura_scraper.slugify("") == "untitled"
    assert trafilatura_scraper.slugify(None) == "untitled"
    assert trafilatura_scraper.slugify("A" * 200) == "a" * 100  # Should be truncated

    # Test format_article_markdown with minimal data
    minimal_data = {"title": "Test", "text": "Content"}
    markdown = trafilatura_scraper.format_article_markdown(minimal_data, "Content")
    assert "# Test" in markdown
    assert "Content" in markdown

def test_api_rate_limiting_placeholder():
    """Placeholder test for rate limiting (to be implemented)"""
    # This test will be updated when rate limiting is implemented
    response = client.get("/health")
    assert response.status_code == 200
    # TODO: Add actual rate limiting tests when implemented

def test_api_authentication_placeholder():
    """Placeholder test for authentication (to be implemented)"""
    # This test will be updated when authentication is implemented
    response = client.get("/")
    assert response.status_code == 200
    # TODO: Add actual authentication tests when implemented

def test_api_batch_processing_placeholder():
    """Placeholder test for batch processing (to be implemented)"""
    # This test will be updated when batch processing is implemented
    response = client.get("/")
    assert response.status_code == 200
    # TODO: Add actual batch processing tests when implemented

@pytest.mark.slow
def test_scraper_network_errors():
    """Test network error handling in scraper"""
    with patch('trafilatura.fetch_url') as mock_fetch, \
         patch('requests.get') as mock_requests:

        # Mock network errors
        mock_fetch.side_effect = Exception("Network error")
        mock_requests.side_effect = Exception("Connection error")

        result_data, result_text = trafilatura_scraper.scrape_article_with_trafilatura("https://test.com")

        assert result_data is None
        assert result_text is not None
        assert "error" in result_text.lower()

@pytest.mark.slow
def test_scraper_timeout_handling():
    """Test timeout handling in scraper"""
    with patch('trafilatura.fetch_url') as mock_fetch, \
         patch('requests.get') as mock_requests:

        # Mock timeout errors
        mock_fetch.side_effect = TimeoutError("Request timed out")
        mock_requests.side_effect = TimeoutError("Connection timed out")

        result_data, result_text = trafilatura_scraper.scrape_article_with_trafilatura("https://test.com")

        assert result_data is None
        assert result_text is not None
        assert "timeout" in result_text.lower() or "error" in result_text.lower()