import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from api.main import app
import trafilatura_scraper

# Create test client
client = TestClient(app)

# ============================================================================
# Authentication Helper Functions
# ============================================================================

def get_test_token() -> str:
    """Get a valid authentication token for testing"""
    response = client.post(
        "/token",
        data={
            "username": "testuser",
            "password": "testpassword"
        }
    )
    assert response.status_code == 200, f"Failed to get token: {response.json()}"
    return response.json()["access_token"]

def get_auth_headers() -> dict:
    """Get authentication headers with a valid token"""
    token = get_test_token()
    return {"Authorization": f"Bearer {token}"}

# ============================================================================
# Tests for Scraper Functions (No auth needed - these test the scraper directly)
# ============================================================================

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

# ============================================================================
# Tests for Public API Endpoints (No auth needed)
# ============================================================================

def test_public_endpoints_no_auth():
    """Test that public endpoints work without authentication"""
    # Health check should be public
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

    # Root endpoint should be public
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

# ============================================================================
# Tests for Authentication System
# ============================================================================

def test_authentication_login():
    """Test the authentication login flow"""
    # Valid credentials should return a token
    response = client.post(
        "/token",
        data={
            "username": "testuser",
            "password": "testpassword"
        }
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

    # Invalid credentials should fail
    response = client.post(
        "/token",
        data={
            "username": "wronguser",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401

def test_protected_endpoints_require_auth():
    """Test that protected endpoints require authentication"""
    # Scrape endpoint should require auth
    response = client.post("/scrape", json={"url": "https://test.com"})
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]

    # Batch scrape should require auth
    response = client.post("/batch-scrape", json={"urls": ["https://test.com"]})
    assert response.status_code == 401

def test_invalid_token_rejected():
    """Test that invalid tokens are rejected"""
    headers = {"Authorization": "Bearer invalid-token-12345"}
    response = client.post(
        "/scrape",
        json={"url": "https://test.com"},
        headers=headers
    )
    assert response.status_code == 401

# ============================================================================
# Tests for Protected API Endpoints (With auth)
# ============================================================================

@pytest.mark.slow
def test_api_error_scenarios():
    """Test various error scenarios in the API with authentication"""
    headers = get_auth_headers()
    
    # Test with malformed URL
    response = client.post(
        "/scrape",
        json={"url": "not-a-valid-url"},
        headers=headers
    )
    assert response.status_code in [400, 500]  # Either bad request or internal error

    # Test with empty URL
    response = client.post(
        "/scrape",
        json={"url": ""},
        headers=headers
    )
    assert response.status_code in [400, 500]

def test_api_request_validation():
    """Test request validation in the API"""
    headers = get_auth_headers()
    
    # Test missing required fields
    response = client.post(
        "/scrape",
        json={},
        headers=headers
    )
    assert response.status_code == 422  # Unprocessable Entity

    # Test invalid data types
    response = client.post(
        "/scrape",
        json={"url": 123},  # URL should be string
        headers=headers
    )
    assert response.status_code == 422

def test_api_exception_handling():
    """Test that the API handles exceptions gracefully"""
    headers = get_auth_headers()
    
    with patch('api.main.trafilatura_scraper.scrape_article_with_trafilatura') as mock_scrape:
        # Mock an exception
        mock_scrape.side_effect = Exception("Test exception")

        response = client.post(
            "/scrape",
            json={"url": "https://test.com"},
            headers=headers
        )
        assert response.status_code == 500
        assert "Error scraping URL" in response.json()["detail"]

def test_api_logging():
    """Test that API operations are properly logged"""
    headers = get_auth_headers()
    
    with patch('api.main.logging') as mock_logging:
        # Test successful request
        with patch('api.main.trafilatura_scraper.scrape_article_with_trafilatura') as mock_scrape:
            mock_scrape.return_value = (
                {"url": "https://test.com", "title": "Test"},
                "Test content"
            )

            response = client.post(
                "/scrape",
                json={"url": "https://test.com"},
                headers=headers
            )
            assert response.status_code == 200

            # Check that logging was called
            mock_logging.info.assert_called()
            mock_logging.error.assert_not_called()

        # Test failed request
        with patch('api.main.trafilatura_scraper.scrape_article_with_trafilatura') as mock_scrape:
            mock_scrape.return_value = (None, "Test error")

            response = client.post(
                "/scrape",
                json={"url": "https://test.com"},
                headers=headers
            )
            assert response.status_code == 400

            # Check that error logging was called
            mock_logging.error.assert_called()

def test_batch_scrape_with_auth():
    """Test batch scraping with authentication"""
    headers = get_auth_headers()
    
    with patch('api.main.trafilatura_scraper.scrape_article_with_trafilatura') as mock_scrape:
        # Mock successful scraping
        mock_scrape.return_value = (
            {"url": "https://test.com", "title": "Test"},
            "Test content"
        )

        response = client.post(
            "/batch-scrape",
            json={
                "urls": ["https://test1.com", "https://test2.com"],
                "include_raw_text": False
            },
            headers=headers
        )
        
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 2
        assert all(r["success"] for r in results)

# ============================================================================
# Placeholder Tests for Future Features
# ============================================================================

def test_api_rate_limiting_placeholder():
    """Placeholder test for rate limiting (to be implemented)"""
    # This test will be updated when rate limiting is implemented
    response = client.get("/health")
    assert response.status_code == 200
    # TODO: Add actual rate limiting tests when implemented

def test_api_caching_placeholder():
    """Placeholder test for caching (to be implemented)"""
    # This test will be updated when caching is implemented
    headers = get_auth_headers()
    response = client.post(
        "/scrape",
        json={"url": "https://test.com"},
        headers=headers
    )
    # TODO: Test that repeated requests use cache
    # TODO: Test cache expiration
    # TODO: Test cache invalidation

def test_api_timeout_handling_placeholder():
    """Placeholder test for timeout handling (to be implemented)"""
    # This test will be updated when timeout handling is implemented
    headers = get_auth_headers()
    # TODO: Test that long-running scrapes timeout appropriately
    # TODO: Test timeout configuration