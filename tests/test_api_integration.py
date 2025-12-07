import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
from api.main import app, ScrapeRequest, ScrapeResponse

# Create test client
client = TestClient(app)

def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "Trafilatura Scraper API"
    assert data["version"] == "1.0.0"
    assert "endpoints" in data
    assert "/scrape" in data["endpoints"]
    assert "/health" in data["endpoints"]

def test_health_endpoint():
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "trafilatura-scraper-api"

@pytest.fixture
def mock_scraper():
    """Mock the scraper functions for API testing"""
    with patch('api.main.trafilatura_scraper.scrape_article_with_trafilatura') as mock_scrape:
        yield mock_scrape

def test_scrape_endpoint_success(mock_scraper):
    """Test successful scraping via API"""
    # Mock successful scraping result
    mock_scraper.return_value = (
        {
            "url": "https://test.com/article",
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
            "raw_text": "Raw text content",
            "source": "test-source",
            "source_hostname": "test-hostname",
            "scraped_at": "2023-01-01T00:00:00"
        },
        "Raw text content"
    )

    # Test request
    request_data = {
        "url": "https://test.com/article",
        "include_raw_text": True,
        "include_metadata": True
    }

    response = client.post("/scrape", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["url"] == "https://test.com/article"
    assert data["data"]["title"] == "Test Article"
    assert data["text_content"] == "Raw text content"
    assert data["error"] is None

def test_scrape_endpoint_failure(mock_scraper):
    """Test failed scraping via API"""
    # Mock failed scraping result
    mock_scraper.return_value = (None, "Scraping failed: Invalid URL")

    # Test request
    request_data = {
        "url": "https://invalid.com/article",
        "include_raw_text": True,
        "include_metadata": True
    }

    response = client.post("/scrape", json=request_data)
    assert response.status_code == 400

    data = response.json()
    assert data["detail"] == "Scraping failed: Invalid URL"

def test_scrape_endpoint_exception(mock_scraper):
    """Test exception handling in API"""
    # Mock exception in scraper
    mock_scraper.side_effect = Exception("Unexpected error occurred")

    # Test request
    request_data = {
        "url": "https://test.com/article",
        "include_raw_text": True,
        "include_metadata": True
    }

    response = client.post("/scrape", json=request_data)
    assert response.status_code == 500

    data = response.json()
    assert "Error scraping URL" in data["detail"]
    assert "Unexpected error occurred" in data["detail"]

def test_scrape_endpoint_without_raw_text(mock_scraper):
    """Test API response when raw text is not requested"""
    # Mock successful scraping result
    mock_scraper.return_value = (
        {
            "url": "https://test.com/article",
            "title": "Test Article",
            "text": "Test text content",
            "raw_text": "Raw text content",
            "scraped_at": "2023-01-01T00:00:00"
        },
        "Raw text content"
    )

    # Test request without raw text
    request_data = {
        "url": "https://test.com/article",
        "include_raw_text": False,
        "include_metadata": True
    }

    response = client.post("/scrape", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["text_content"] is None  # Should be None when not requested

@pytest.mark.slow
def test_scrape_endpoint_validation():
    """Test request validation"""
    # Test missing URL
    request_data = {
        "include_raw_text": True,
        "include_metadata": True
    }

    response = client.post("/scrape", json=request_data)
    assert response.status_code == 422  # Unprocessable Entity

    # Test invalid URL format
    request_data = {
        "url": "not-a-valid-url",
        "include_raw_text": True,
        "include_metadata": True
    }

    response = client.post("/scrape", json=request_data)
    # Should still accept it (URL validation happens in scraper)
    assert response.status_code in [200, 400]  # Either success or bad request

def test_scrape_request_model():
    """Test the ScrapeRequest Pydantic model"""
    # Test valid request
    request = ScrapeRequest(
        url="https://test.com/article",
        include_raw_text=True,
        include_metadata=False
    )

    assert request.url == "https://test.com/article"
    assert request.include_raw_text is True
    assert request.include_metadata is False

    # Test default values
    request_default = ScrapeRequest(url="https://test.com/article")
    assert request_default.include_raw_text is True
    assert request_default.include_metadata is True

def test_scrape_response_model():
    """Test the ScrapeResponse Pydantic model"""
    # Test successful response
    response = ScrapeResponse(
        success=True,
        data={"title": "Test"},
        text_content="Content",
        error=None,
        url="https://test.com"
    )

    assert response.success is True
    assert response.data == {"title": "Test"}
    assert response.text_content == "Content"
    assert response.error is None
    assert response.url == "https://test.com"

    # Test failed response
    response_fail = ScrapeResponse(
        success=False,
        data=None,
        text_content=None,
        error="Error occurred",
        url="https://test.com"
    )

    assert response_fail.success is False
    assert response_fail.data is None
    assert response_fail.error == "Error occurred"

def test_api_cors_headers():
    """Test CORS headers are properly configured"""
    response = client.get("/")
    assert response.status_code == 200

    # Check CORS headers
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "*"

def test_api_error_handling():
    """Test API error handling for malformed requests"""
    # Test with empty request
    response = client.post("/scrape", json={})
    assert response.status_code == 422  # Unprocessable Entity