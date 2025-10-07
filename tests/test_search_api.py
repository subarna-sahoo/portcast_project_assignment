import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from backend.commons.models import Paragraph


class TestSearchAPI:
    """Test cases for the /search endpoint"""

    @pytest.mark.asyncio
    async def test_search_with_and_operator_success(self, client, test_db):
        """Test successful search with AND operator"""
        # Setup: Add test paragraphs to database
        p1 = Paragraph(id=1, content="Python is a programming language", created_at=datetime.now())
        p2 = Paragraph(id=2, content="Python programming is fun", created_at=datetime.now())
        p3 = Paragraph(id=3, content="JavaScript is also a language", created_at=datetime.now())
        test_db.add_all([p1, p2, p3])
        await test_db.commit()

        # Mock Elasticsearch response
        with patch('backend.commons.elasticsearch_client.ElasticsearchClient.search') as mock_es_search:
            mock_es_search.return_value = {
                "hits": {
                    "hits": [
                        {"_id": "1", "_score": 2.5},
                        {"_id": "2", "_score": 2.0}
                    ]
                }
            }

            # Make request
            response = await client.post(
                "/api/search",
                json={"words": ["python", "programming"], "operator": "and"}
            )

            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert "paragraphs" in data
            assert data["total"] == 2
            assert len(data["paragraphs"]) == 2
            # Verify the paragraphs contain expected data
            assert any(p["id"] == 1 for p in data["paragraphs"])
            assert any(p["id"] == 2 for p in data["paragraphs"])

    @pytest.mark.asyncio
    async def test_search_with_or_operator_success(self, client, test_db):
        """Test successful search with OR operator"""
        # Setup: Add test paragraphs to database
        p1 = Paragraph(id=1, content="Python is a programming language", created_at=datetime.now())
        p2 = Paragraph(id=2, content="Ruby is a gem", created_at=datetime.now())
        p3 = Paragraph(id=3, content="JavaScript frameworks", created_at=datetime.now())
        test_db.add_all([p1, p2, p3])
        await test_db.commit()

        # Mock Elasticsearch response
        with patch('backend.commons.elasticsearch_client.ElasticsearchClient.search') as mock_es_search:
            mock_es_search.return_value = {
                "hits": {
                    "hits": [
                        {"_id": "1", "_score": 2.5},
                        {"_id": "2", "_score": 1.8},
                        {"_id": "3", "_score": 1.5}
                    ]
                }
            }

            # Make request
            response = await client.post(
                "/api/search",
                json={"words": ["python", "ruby", "javascript"], "operator": "or"}
            )

            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert "paragraphs" in data
            assert data["total"] == 3
            assert len(data["paragraphs"]) == 3

    @pytest.mark.asyncio
    async def test_search_no_results(self, client, test_db):
        """Test search with no matching results"""
        # Setup: Add test paragraph to database
        p1 = Paragraph(id=1, content="Python programming", created_at=datetime.now())
        test_db.add(p1)
        await test_db.commit()

        # Mock Elasticsearch response with no hits
        with patch('backend.commons.elasticsearch_client.ElasticsearchClient.search') as mock_es_search:
            mock_es_search.return_value = {
                "hits": {
                    "hits": []
                }
            }

            # Make request
            response = await client.post(
                "/api/search",
                json={"words": ["nonexistent", "words"], "operator": "and"}
            )

            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["paragraphs"] == []
            assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_search_single_word(self, client, test_db):
        """Test search with a single word"""
        # Setup: Add test paragraphs
        p1 = Paragraph(id=1, content="FastAPI is awesome", created_at=datetime.now())
        p2 = Paragraph(id=2, content="FastAPI framework", created_at=datetime.now())
        test_db.add_all([p1, p2])
        await test_db.commit()

        # Mock Elasticsearch response
        with patch('backend.commons.elasticsearch_client.ElasticsearchClient.search') as mock_es_search:
            mock_es_search.return_value = {
                "hits": {
                    "hits": [
                        {"_id": "1", "_score": 3.0},
                        {"_id": "2", "_score": 2.8}
                    ]
                }
            }

            # Make request
            response = await client.post(
                "/api/search",
                json={"words": ["fastapi"], "operator": "and"}
            )

            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["paragraphs"]) == 2

    @pytest.mark.asyncio
    async def test_search_invalid_operator(self, client, test_db):
        """Test search with invalid operator"""
        # Make request with invalid operator
        response = await client.post(
            "/api/search",
            json={"words": ["test"], "operator": "invalid"}
        )

        # Assertions - should fail validation
        assert response.status_code == 422  # Unprocessable Entity

    @pytest.mark.asyncio
    async def test_search_empty_words_list(self, client, test_db):
        """Test search with empty words list"""
        # Mock Elasticsearch to return no results for empty search
        with patch('backend.commons.elasticsearch_client.ElasticsearchClient.search') as mock_es_search:
            mock_es_search.return_value = {
                "hits": {
                    "hits": []
                }
            }

            # Make request with empty words
            response = await client.post(
                "/api/search",
                json={"words": [], "operator": "and"}
            )

            # Assertions
            assert response.status_code == 200
            # With empty words, ES should return no results
            data = response.json()
            assert data["paragraphs"] == []
            assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_search_elasticsearch_failure(self, client, test_db):
        """Test search when Elasticsearch fails"""
        # Setup: Add test paragraph
        p1 = Paragraph(id=1, content="Test content", created_at=datetime.now())
        test_db.add(p1)
        await test_db.commit()

        # Mock Elasticsearch to raise an exception
        with patch('backend.commons.elasticsearch_client.ElasticsearchClient.search') as mock_es_search:
            mock_es_search.side_effect = Exception("Elasticsearch connection error")

            # Make request
            response = await client.post(
                "/api/search",
                json={"words": ["test"], "operator": "and"}
            )

            # Assertions - should return 500 error
            assert response.status_code == 500
            assert "detail" in response.json()

    @pytest.mark.asyncio
    async def test_search_maintains_elasticsearch_ranking(self, client, test_db):
        """Test that search results maintain Elasticsearch ranking order"""
        # Setup: Add test paragraphs
        p1 = Paragraph(id=1, content="First paragraph", created_at=datetime.now())
        p2 = Paragraph(id=2, content="Second paragraph", created_at=datetime.now())
        p3 = Paragraph(id=3, content="Third paragraph", created_at=datetime.now())
        test_db.add_all([p1, p2, p3])
        await test_db.commit()

        # Mock Elasticsearch response with specific ranking
        with patch('backend.commons.elasticsearch_client.ElasticsearchClient.search') as mock_es_search:
            mock_es_search.return_value = {
                "hits": {
                    "hits": [
                        {"_id": "3", "_score": 5.0},  # Highest score
                        {"_id": "1", "_score": 3.0},
                        {"_id": "2", "_score": 2.0}   # Lowest score
                    ]
                }
            }

            # Make request
            response = await client.post(
                "/api/search",
                json={"words": ["paragraph"], "operator": "and"}
            )

            # Assertions
            assert response.status_code == 200
            data = response.json()
            # Verify order matches ES ranking
            assert data["paragraphs"][0]["id"] == 3  # Highest score first
            assert data["paragraphs"][1]["id"] == 1
            assert data["paragraphs"][2]["id"] == 2  # Lowest score last

    @pytest.mark.asyncio
    async def test_search_with_fuzziness(self, client, test_db):
        """Test that search applies fuzziness for typo tolerance"""
        # Setup: Add test paragraph
        p1 = Paragraph(id=1, content="Python programming language", created_at=datetime.now())
        test_db.add(p1)
        await test_db.commit()

        # Mock Elasticsearch response (fuzziness is handled by ES)
        with patch('backend.commons.elasticsearch_client.ElasticsearchClient.search') as mock_es_search:
            # Verify that the search query includes fuzziness parameter
            mock_es_search.return_value = {
                "hits": {
                    "hits": [
                        {"_id": "1", "_score": 2.0}
                    ]
                }
            }

            # Make request with slight typo
            response = await client.post(
                "/api/search",
                json={"words": ["pyhton"], "operator": "and"}  # Typo: pyhton instead of python
            )

            # Assertions
            assert response.status_code == 200
            # Verify that ES search was called with fuzziness in the query
            call_args = mock_es_search.call_args
            query = call_args.kwargs['query']
            # Check that fuzziness is set to 2 in the query
            assert query['bool']['must'][0]['match']['content']['fuzziness'] == 2

    @pytest.mark.asyncio
    async def test_search_response_schema(self, client, test_db):
        """Test that search response matches expected schema"""
        # Setup: Add test paragraph
        p1 = Paragraph(id=1, content="Schema test content", created_at=datetime.now())
        test_db.add(p1)
        await test_db.commit()

        # Mock Elasticsearch response
        with patch('backend.commons.elasticsearch_client.ElasticsearchClient.search') as mock_es_search:
            mock_es_search.return_value = {
                "hits": {
                    "hits": [
                        {"_id": "1", "_score": 1.5}
                    ]
                }
            }

            # Make request
            response = await client.post(
                "/api/search",
                json={"words": ["schema"], "operator": "and"}
            )

            # Assertions
            assert response.status_code == 200
            data = response.json()
            # Verify response structure
            assert "paragraphs" in data
            assert "total" in data
            assert isinstance(data["paragraphs"], list)
            assert isinstance(data["total"], int)
            # Verify paragraph structure
            if data["paragraphs"]:
                paragraph = data["paragraphs"][0]
                assert "id" in paragraph
                assert "content" in paragraph
                assert "created_at" in paragraph

    @pytest.mark.asyncio
    async def test_search_missing_required_fields(self, client, test_db):
        """Test search with missing required fields"""
        # Test missing 'operator' field
        response = await client.post(
            "/api/search",
            json={"words": ["test"]}
        )
        assert response.status_code == 422

        # Test missing 'words' field
        response = await client.post(
            "/api/search",
            json={"operator": "and"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_limits_results_to_10(self, client, test_db):
        """Test that search limits results to 10 items"""
        # Setup: Add 15 test paragraphs
        paragraphs = [
            Paragraph(id=i, content=f"Paragraph {i} content", created_at=datetime.now())
            for i in range(1, 16)
        ]
        test_db.add_all(paragraphs)
        await test_db.commit()

        # Mock Elasticsearch response with 15 hits
        with patch('backend.commons.elasticsearch_client.ElasticsearchClient.search') as mock_es_search:
            mock_es_search.return_value = {
                "hits": {
                    "hits": [{"_id": str(i), "_score": 10.0 - i * 0.1} for i in range(1, 11)]
                }
            }

            # Make request
            response = await client.post(
                "/api/search",
                json={"words": ["paragraph"], "operator": "or"}
            )

            # Assertions
            assert response.status_code == 200
            data = response.json()
            # Verify that ES search was called with size=10
            call_args = mock_es_search.call_args
            assert call_args.kwargs['size'] == 10
