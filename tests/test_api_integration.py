"""
Integration tests for the Scraper API

These tests verify end-to-end functionality including:
- Authentication flow
- Scraping real URLs (or well-mocked ones)
- Batch processing
- Error handling across the full stack
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from unittest.mock import patch, MagicMock

# Create test client
client = TestClient(app)

# ============================================================================
# Authentication Helpers
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
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_successful_scrape():
    """Fixture that mocks a successful scraping operation"""
    mock_data = {
        "url": "https://example.com/article",
        "title": "Test Article Title",
        "author": "Test Author",
        "date": "2024-12-07",
        "sitename": "Example Site",
        "categories": ["Technology"],
        "tags": ["test", "article"],
        "text": "This is the main article content.",
    }
    mock_text = "This is the main article content."
    
    with patch('api.main.trafilatura_scraper.scrape_article_with_trafilatura') as mock:
        mock.return_value = (mock_data, mock_text)
        yield mock

@pytest.fixture
def mock_failed_scrape():
    """Fixture that mocks a failed scraping operation"""
    with patch('api.main.trafilatura_scraper.scrape_article_with_trafilatura') as mock:
        mock.return_value = (None, "Failed to fetch or parse the article")
        yield mock

# ============================================================================
# Basic API Integration Tests
# ============================================================================

def test_api_root_endpoint():
    """Test that the root endpoint returns API information"""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "endpoints" in data
    assert data["message"] == "Trafilatura Scraper API"

def test_health_check_endpoint():
    """Test the health check endpoint"""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "trafilatura-scraper-api"

def test_api_documentation_accessible():
    """Test that API documentation endpoints are accessible"""
    # Test OpenAPI schema
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "openapi" in response.json()
    
    # Test Swagger UI (docs)
    response = client.get("/docs")
    assert response.status_code == 200
    
    # Test ReDoc
    response = client.get("/redoc")
    assert response.status_code == 200

# ============================================================================
# Authentication Integration Tests
# ============================================================================

def test_complete_authentication_flow():
    """Test the complete authentication flow from login to authenticated request"""
    # Step 1: Login and get token
    login_response = client.post(
        "/token",
        data={
            "username": "testuser",
            "password": "testpassword"
        }
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    
    # Step 2: Use token to make authenticated request
    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    with patch('api.main.trafilatura_scraper.scrape_article_with_trafilatura') as mock:
        mock.return_value = (
            {"url": "https://test.com", "title": "Test"},
            "Test content"
        )
        
        scrape_response = client.post(
            "/scrape",
            json={"url": "https://test.com"},
            headers=headers
        )
        assert scrape_response.status_code == 200

def test_authentication_failures():
    """Test various authentication failure scenarios"""
    # Test with wrong username
    response = client.post(
        "/token",
        data={
            "username": "wronguser",
            "password": "testpassword"
        }
    )
    assert response.status_code == 401
    
    # Test with wrong password
    response = client.post(
        "/token",
        data={
            "username": "testuser",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    
    # Test accessing protected endpoint without token
    response = client.post(
        "/scrape",
        json={"url": "https://test.com"}
    )
    assert response.status_code == 401
    
    # Test with invalid token format
    response = client.post(
        "/scrape",
        json={"url": "https://test.com"},
        headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401

def test_token_in_request_header():
    """Test that token must be in Authorization header"""
    token = get_test_token()
    
    # Test with correct header format
    with patch('api.main.trafilatura_scraper.scrape_article_with_trafilatura') as mock:
        mock.return_value = ({"url": "test.com"}, "content")
        
        response = client.post(
            "/scrape",
            json={"url": "https://test.com"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
    
    # Test with token in wrong place (query param, body, etc. should fail)
    response = client.post(
        "/scrape",
        json={"url": "https://test.com", "token": token}
    )
    assert response.status_code == 401

# ============================================================================
# Scraping Integration Tests
# ============================================================================

def test_successful_article_scrape(mock_successful_scrape):
    """Test successful article scraping with all components"""
    headers = get_auth_headers()
    
    response = client.post(
        "/scrape",
        json={
            "url": "https://example.com/article",
            "include_raw_text": True,
            "include_metadata": True
        },
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert data["success"] is True
    assert data["url"] == "https://example.com/article"
    assert data["error"] is None
    
    # Verify article data
    assert data["data"] is not None
    assert data["data"]["title"] == "Test Article Title"
    assert data["data"]["author"] == "Test Author"
    assert data["data"]["text"] == "This is the main article content."
    
    # Verify text content
    assert data["text_content"] == "This is the main article content."

def test_scrape_without_raw_text(mock_successful_scrape):
    """Test scraping with include_raw_text=False"""
    headers = get_auth_headers()
    
    response = client.post(
        "/scrape",
        json={
            "url": "https://example.com/article",
            "include_raw_text": False,
            "include_metadata": True
        },
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["text_content"] is None  # Should be None when not requested
    assert data["data"] is not None

def test_failed_article_scrape(mock_failed_scrape):
    """Test handling of failed scraping attempts"""
    headers = get_auth_headers()
    
    response = client.post(
        "/scrape",
        json={"url": "https://example.com/article"},
        headers=headers
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Failed to fetch or parse" in data["detail"]

def test_scrape_with_invalid_url():
    """Test scraping with invalid URL format"""
    headers = get_auth_headers()
    
    with patch('api.main.trafilatura_scraper.scrape_article_with_trafilatura') as mock:
        mock.return_value = (None, "Invalid URL format")
        
        response = client.post(
            "/scrape",
            json={"url": "not-a-valid-url"},
            headers=headers
        )
        
        assert response.status_code == 400

def test_scrape_with_network_error():
    """Test handling of network errors during scraping"""
    headers = get_auth_headers()
    
    with patch('api.main.trafilatura_scraper.scrape_article_with_trafilatura') as mock:
        mock.side_effect = Exception("Network connection failed")
        
        response = client.post(
            "/scrape",
            json={"url": "https://example.com/article"},
            headers=headers
        )
        
        assert response.status_code == 500
        assert "Error scraping URL" in response.json()["detail"]

# ============================================================================
# Batch Scraping Integration Tests
# ============================================================================

def test_batch_scrape_success():
    """Test successful batch scraping of multiple URLs"""
    headers = get_auth_headers()
    
    with patch('api.main.trafilatura_scraper.scrape_article_with_trafilatura') as mock:
        # Mock returns different data for each URL
        def side_effect(url):
            if "article1" in url:
                return ({"url": url, "title": "Article 1"}, "Content 1")
            elif "article2" in url:
                return ({"url": url, "title": "Article 2"}, "Content 2")
            return ({"url": url, "title": "Article 3"}, "Content 3")
        
        mock.side_effect = side_effect
        
        response = client.post(
            "/batch-scrape",
            json={
                "urls": [
                    "https://example.com/article1",
                    "https://example.com/article2",
                    "https://example.com/article3"
                ],
                "include_raw_text": True,
                "include_metadata": True
            },
            headers=headers
        )
        
        assert response.status_code == 200
        results = response.json()
        
        # Verify we got results for all URLs
        assert len(results) == 3
        
        # Verify all succeeded
        assert all(r["success"] for r in results)
        
        # Verify data for each
        assert results[0]["data"]["title"] == "Article 1"
        assert results[1]["data"]["title"] == "Article 2"
        assert results[2]["data"]["title"] == "Article 3"

def test_batch_scrape_partial_failure():
    """Test batch scraping where some URLs fail"""
    headers = get_auth_headers()
    
    with patch('api.main.trafilatura_scraper.scrape_article_with_trafilatura') as mock:
        # First URL succeeds, second fails, third succeeds
        mock.side_effect = [
            ({"url": "url1", "title": "Success 1"}, "Content 1"),
            (None, "Failed to scrape"),
            ({"url": "url3", "title": "Success 3"}, "Content 3"),
        ]
        
        response = client.post(
            "/batch-scrape",
            json={
                "urls": [
                    "https://example.com/article1",
                    "https://example.com/article2",
                    "https://example.com/article3"
                ]
            },
            headers=headers
        )
        
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 3
        
        # Verify success/failure pattern
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert results[2]["success"] is True
        
        # Verify error message for failed URL
        assert results[1]["error"] is not None
        assert "Failed to scrape" in results[1]["error"]

def test_batch_scrape_empty_list():
    """Test batch scraping with empty URL list"""
    headers = get_auth_headers()
    
    response = client.post(
        "/batch-scrape",
        json={"urls": []},
        headers=headers
    )
    
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 0

def test_batch_scrape_single_url():
    """Test batch scraping with single URL (edge case)"""
    headers = get_auth_headers()
    
    with patch('api.main.trafilatura_scraper.scrape_article_with_trafilatura') as mock:
        mock.return_value = ({"url": "test", "title": "Test"}, "Content")
        
        response = client.post(
            "/batch-scrape",
            json={"urls": ["https://example.com/article"]},
            headers=headers
        )
        
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["success"] is True

def test_batch_scrape_without_auth():
    """Test that batch scraping requires authentication"""
    response = client.post(
        "/batch-scrape",
        json={"urls": ["https://example.com/article"]}
    )
    
    assert response.status_code == 401

# ============================================================================
# Request Validation Integration Tests
# ============================================================================

def test_scrape_request_validation():
    """Test request validation for scrape endpoint"""
    headers = get_auth_headers()
    
    # Missing required field (url)
    response = client.post("/scrape", json={}, headers=headers)
    assert response.status_code == 422
    
    # Invalid type for url
    response = client.post("/scrape", json={"url": 123}, headers=headers)
    assert response.status_code == 422
    
    # Invalid type for boolean fields
    response = client.post(
        "/scrape",
        json={
            "url": "https://example.com",
            "include_raw_text": "yes"  # Should be boolean
        },
        headers=headers
    )
    assert response.status_code == 422

def test_batch_scrape_request_validation():
    """Test request validation for batch-scrape endpoint"""
    headers = get_auth_headers()
    
    # Missing required field (urls)
    response = client.post("/batch-scrape", json={}, headers=headers)
    assert response.status_code == 422
    
    # Invalid type for urls (should be list)
    response = client.post(
        "/batch-scrape",
        json={"urls": "https://example.com"},
        headers=headers
    )
    assert response.status_code == 422
    
    # Invalid type for items in urls list
    response = client.post(
        "/batch-scrape",
        json={"urls": [123, 456]},
        headers=headers
    )
    assert response.status_code == 422

# ============================================================================
# CORS Integration Tests
# ============================================================================

def test_cors_headers_present():
    """Test that CORS headers are present in responses"""
    response = client.get("/health")
    
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "*"

def test_cors_preflight_request():
    """Test CORS preflight (OPTIONS) requests"""
    response = client.options(
        "/scrape",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization"
        }
    )
    
    # Should allow the request
    assert "access-control-allow-origin" in response.headers
    assert "access-control-allow-methods" in response.headers

# ============================================================================
# End-to-End Workflow Tests
# ============================================================================

@pytest.mark.slow
def test_complete_workflow_single_scrape():
    """Test complete workflow: login -> scrape -> verify"""
    # Step 1: Login
    login_response = client.post(
        "/token",
        data={"username": "testuser", "password": "testpassword"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Step 2: Scrape an article
    with patch('api.main.trafilatura_scraper.scrape_article_with_trafilatura') as mock:
        mock.return_value = (
            {
                "url": "https://example.com/article",
                "title": "Integration Test Article",
                "text": "Article content for integration testing."
            },
            "Article content for integration testing."
        )
        
        scrape_response = client.post(
            "/scrape",
            json={"url": "https://example.com/article", "include_raw_text": True},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert scrape_response.status_code == 200
        data = scrape_response.json()
        
        # Step 3: Verify response
        assert data["success"] is True
        assert data["data"]["title"] == "Integration Test Article"
        assert data["text_content"] is not None

@pytest.mark.slow
def test_complete_workflow_batch_scrape():
    """Test complete workflow: login -> batch scrape -> verify"""
    # Step 1: Login
    token = get_test_token()
    
    # Step 2: Batch scrape multiple articles
    with patch('api.main.trafilatura_scraper.scrape_article_with_trafilatura') as mock:
        mock.side_effect = [
            ({"url": f"url{i}", "title": f"Article {i}"}, f"Content {i}")
            for i in range(1, 6)
        ]
        
        batch_response = client.post(
            "/batch-scrape",
            json={
                "urls": [f"https://example.com/article{i}" for i in range(1, 6)],
                "include_raw_text": False
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert batch_response.status_code == 200
        results = batch_response.json()
        
        # Step 3: Verify all results
        assert len(results) == 5
        assert all(r["success"] for r in results)
        assert all(r["text_content"] is None for r in results)  # We set include_raw_text=False

@pytest.mark.slow  
def test_multiple_sequential_requests():
    """Test multiple sequential requests with same token"""
    headers = get_auth_headers()
    
    with patch('api.main.trafilatura_scraper.scrape_article_with_trafilatura') as mock:
        mock.return_value = ({"url": "test", "title": "Test"}, "Content")
        
        # Make 5 sequential requests with same token
        for i in range(5):
            response = client.post(
                "/scrape",
                json={"url": f"https://example.com/article{i}"},
                headers=headers
            )
            assert response.status_code == 200
            assert response.json()["success"] is True

# ============================================================================
# Performance and Load Tests (marked as slow)
# ============================================================================

@pytest.mark.slow
def test_large_batch_scrape():
    """Test batch scraping with large number of URLs"""
    headers = get_auth_headers()
    
    with patch('api.main.trafilatura_scraper.scrape_article_with_trafilatura') as mock:
        mock.return_value = ({"url": "test", "title": "Test"}, "Content")
        
        # Test with 50 URLs
        large_url_list = [f"https://example.com/article{i}" for i in range(50)]
        
        response = client.post(
            "/batch-scrape",
            json={"urls": large_url_list, "include_raw_text": False},
            headers=headers
        )
        
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 50
        assert all(r["success"] for r in results)