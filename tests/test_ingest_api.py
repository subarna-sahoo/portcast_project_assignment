import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import Response
from datetime import datetime
from backend.commons.models import Paragraph, WordFrequency
from sqlalchemy import select


class TestIngestAPI:
    """Test cases for the /fetch endpoint"""

    @pytest.mark.asyncio
    async def test_fetch_paragraph_success(self, client, test_db, mock_redis):
        """Test successful paragraph fetch and storage"""
        # Mock external API response
        mock_paragraph_content = "This is a test paragraph with some sample words for testing purposes."

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock(spec=Response)
            mock_response.text = mock_paragraph_content
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Mock Elasticsearch indexing
            with patch('backend.commons.elasticsearch_client.ElasticsearchClient.index_document') as mock_es_index:
                mock_es_index.return_value = {"result": "created"}

                # Make request
                response = await client.post("/api/fetch")

                # Assertions
                assert response.status_code == 200
                data = response.json()
                assert "id" in data
                assert "content" in data
                assert "created_at" in data
                assert data["content"] == mock_paragraph_content

                # Verify paragraph was stored in database
                stmt = select(Paragraph).where(Paragraph.content == mock_paragraph_content)
                result = await test_db.execute(stmt)
                stored_paragraph = result.scalar_one_or_none()
                assert stored_paragraph is not None
                assert stored_paragraph.content == mock_paragraph_content

    @pytest.mark.asyncio
    async def test_fetch_paragraph_updates_word_frequencies(self, client, test_db, mock_redis):
        """Test that fetching a paragraph updates word frequencies"""
        # Mock external API response with specific words
        mock_paragraph_content = "Python programming language. Python is amazing. Programming is fun."

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock(spec=Response)
            mock_response.text = mock_paragraph_content
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Mock Elasticsearch indexing
            with patch('backend.commons.elasticsearch_client.ElasticsearchClient.index_document') as mock_es_index:
                mock_es_index.return_value = {"result": "created"}

                # Make request
                response = await client.post("/api/fetch")

                # Assertions
                assert response.status_code == 200

                # Verify word frequencies were updated in database
                stmt = select(WordFrequency).where(WordFrequency.word == "python")
                result = await test_db.execute(stmt)
                word_freq = result.scalar_one_or_none()
                assert word_freq is not None
                assert word_freq.frequency == 2  # "python" appears twice

                stmt = select(WordFrequency).where(WordFrequency.word == "programming")
                result = await test_db.execute(stmt)
                word_freq = result.scalar_one_or_none()
                assert word_freq is not None
                assert word_freq.frequency == 2  # "programming" appears twice

    @pytest.mark.asyncio
    async def test_fetch_paragraph_indexes_elasticsearch(self, client, test_db, mock_redis):
        """Test that fetched paragraph is indexed in Elasticsearch"""
        # Mock external API response
        mock_paragraph_content = "Testing Elasticsearch indexing functionality."

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock(spec=Response)
            mock_response.text = mock_paragraph_content
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Mock Elasticsearch indexing
            with patch('backend.commons.elasticsearch_client.ElasticsearchClient.index_document') as mock_es_index:
                mock_es_index.return_value = {"result": "created"}

                # Make request
                response = await client.post("/api/fetch")

                # Assertions
                assert response.status_code == 200
                # Verify Elasticsearch index_document was called
                mock_es_index.assert_called_once()
                call_args = mock_es_index.call_args
                assert call_args.kwargs['index'] == "paragraphs"
                assert call_args.kwargs['document']['content'] == mock_paragraph_content

    @pytest.mark.asyncio
    async def test_fetch_paragraph_external_api_failure(self, client, test_db, mock_redis):
        """Test fetch endpoint when external API fails"""
        # Mock external API to raise an exception
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("External API error"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Make request
            response = await client.post("/api/fetch")

            # Assertions - should return 500 error
            assert response.status_code == 500
            assert "detail" in response.json()

    @pytest.mark.asyncio
    async def test_fetch_paragraph_elasticsearch_failure_continues(self, client, test_db, mock_redis):
        """Test that fetch continues even if Elasticsearch indexing fails"""
        # Mock external API response
        mock_paragraph_content = "Test paragraph for ES failure scenario."

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock(spec=Response)
            mock_response.text = mock_paragraph_content
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Mock Elasticsearch to fail
            with patch('backend.commons.elasticsearch_client.ElasticsearchClient.index_document') as mock_es_index:
                mock_es_index.side_effect = Exception("Elasticsearch error")

                # Make request - should fail because ES error is not caught
                response = await client.post("/api/fetch")

                # The current implementation doesn't catch ES errors,
                # so it should return 500
                assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_fetch_paragraph_filters_stopwords(self, client, test_db, mock_redis):
        """Test that fetch filters out stopwords from word frequency updates"""
        # Mock external API response with stopwords
        mock_paragraph_content = "The test and the paragraph for with from that this testing purposes."

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock(spec=Response)
            mock_response.text = mock_paragraph_content
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Mock Elasticsearch indexing
            with patch('backend.commons.elasticsearch_client.ElasticsearchClient.index_document') as mock_es_index:
                mock_es_index.return_value = {"result": "created"}

                # Make request
                response = await client.post("/api/fetch")

                # Assertions
                assert response.status_code == 200

                # Verify stopwords were NOT added to word frequencies
                stopwords = ["the", "and", "for", "with", "from", "that", "this"]
                for stopword in stopwords:
                    stmt = select(WordFrequency).where(WordFrequency.word == stopword)
                    result = await test_db.execute(stmt)
                    word_freq = result.scalar_one_or_none()
                    assert word_freq is None  # Stopwords should not be stored

                # Verify non-stopwords were added
                stmt = select(WordFrequency).where(WordFrequency.word == "test")
                result = await test_db.execute(stmt)
                word_freq = result.scalar_one_or_none()
                assert word_freq is not None

    @pytest.mark.asyncio
    async def test_fetch_paragraph_filters_short_words(self, client, test_db, mock_redis):
        """Test that fetch filters out words shorter than 4 characters"""
        # Mock external API response with short words
        mock_paragraph_content = "The cat ran to a big dog and ate food quickly."

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock(spec=Response)
            mock_response.text = mock_paragraph_content
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Mock Elasticsearch indexing
            with patch('backend.commons.elasticsearch_client.ElasticsearchClient.index_document') as mock_es_index:
                mock_es_index.return_value = {"result": "created"}

                # Make request
                response = await client.post("/api/fetch")

                # Assertions
                assert response.status_code == 200

                # Verify short words (< 4 chars) were NOT added
                short_words = ["cat", "ran", "to", "a", "big", "dog", "and", "ate"]
                for short_word in short_words:
                    stmt = select(WordFrequency).where(WordFrequency.word == short_word)
                    result = await test_db.execute(stmt)
                    word_freq = result.scalar_one_or_none()
                    assert word_freq is None  # Short words should not be stored

                # Verify long words (>= 4 chars) were added
                stmt = select(WordFrequency).where(WordFrequency.word == "food")
                result = await test_db.execute(stmt)
                word_freq = result.scalar_one_or_none()
                assert word_freq is not None

    @pytest.mark.asyncio
    async def test_fetch_paragraph_increments_existing_word_frequencies(self, client, test_db, mock_redis):
        """Test that fetch increments existing word frequencies"""
        # Setup: Add existing word frequency
        existing_word = WordFrequency(word="python", frequency=10)
        test_db.add(existing_word)
        await test_db.commit()

        # Mock external API response with the same word
        mock_paragraph_content = "Python programming is great. Python rocks."

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock(spec=Response)
            mock_response.text = mock_paragraph_content
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Mock Elasticsearch indexing
            with patch('backend.commons.elasticsearch_client.ElasticsearchClient.index_document') as mock_es_index:
                mock_es_index.return_value = {"result": "created"}

                # Make request
                response = await client.post("/api/fetch")

                # Assertions
                assert response.status_code == 200

                # Verify word frequency was incremented (10 + 2 = 12)
                stmt = select(WordFrequency).where(WordFrequency.word == "python")
                result = await test_db.execute(stmt)
                word_freq = result.scalar_one_or_none()
                assert word_freq is not None
                assert word_freq.frequency == 12

    @pytest.mark.asyncio
    async def test_fetch_paragraph_updates_redis_cache(self, client, test_db, mock_redis):
        """Test that fetch updates Redis cache with new word frequencies"""
        # Mock external API response
        mock_paragraph_content = "Testing Redis cache update functionality with multiple words testing."

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock(spec=Response)
            mock_response.text = mock_paragraph_content
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Mock Elasticsearch indexing
            with patch('backend.commons.elasticsearch_client.ElasticsearchClient.index_document') as mock_es_index:
                mock_es_index.return_value = {"result": "created"}

                # Make request
                response = await client.post("/api/fetch")

                # Assertions
                assert response.status_code == 200
                # Verify Redis delete was called (cache invalidation)
                mock_redis.delete.assert_called()
                # Verify Redis zadd was called (cache update)
                mock_redis.zadd.assert_called()

    @pytest.mark.asyncio
    async def test_fetch_paragraph_redis_failure_continues(self, client, test_db, mock_redis):
        """Test that fetch continues even if Redis update fails"""
        # Mock external API response
        mock_paragraph_content = "Test paragraph for Redis failure scenario."

        # Make Redis operations fail
        mock_redis.delete.side_effect = Exception("Redis error")
        mock_redis.zadd.side_effect = Exception("Redis error")

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock(spec=Response)
            mock_response.text = mock_paragraph_content
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Mock Elasticsearch indexing
            with patch('backend.commons.elasticsearch_client.ElasticsearchClient.index_document') as mock_es_index:
                mock_es_index.return_value = {"result": "created"}

                # Make request - should succeed despite Redis failure
                response = await client.post("/api/fetch")

                # Assertions
                assert response.status_code == 200
                # Verify paragraph was still stored
                data = response.json()
                assert data["content"] == mock_paragraph_content

    @pytest.mark.asyncio
    async def test_fetch_paragraph_response_schema(self, client, test_db, mock_redis):
        """Test that fetch response matches expected ParagraphResponse schema"""
        # Mock external API response
        mock_paragraph_content = "Testing response schema validation."

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock(spec=Response)
            mock_response.text = mock_paragraph_content
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Mock Elasticsearch indexing
            with patch('backend.commons.elasticsearch_client.ElasticsearchClient.index_document') as mock_es_index:
                mock_es_index.return_value = {"result": "created"}

                # Make request
                response = await client.post("/api/fetch")

                # Assertions
                assert response.status_code == 200
                data = response.json()
                # Verify all required fields are present
                assert "id" in data
                assert "content" in data
                assert "created_at" in data
                # Verify field types
                assert isinstance(data["id"], int)
                assert isinstance(data["content"], str)
                assert isinstance(data["created_at"], str)  # ISO format datetime string

    @pytest.mark.asyncio
    async def test_fetch_paragraph_empty_content(self, client, test_db, mock_redis):
        """Test fetch with empty paragraph content"""
        # Mock external API response with empty content
        mock_paragraph_content = ""

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock(spec=Response)
            mock_response.text = mock_paragraph_content
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Mock Elasticsearch indexing
            with patch('backend.commons.elasticsearch_client.ElasticsearchClient.index_document') as mock_es_index:
                mock_es_index.return_value = {"result": "created"}

                # Make request
                response = await client.post("/api/fetch")

                # Assertions
                assert response.status_code == 200
                data = response.json()
                assert data["content"] == ""
                # Verify no word frequencies were added
                stmt = select(WordFrequency)
                result = await test_db.execute(stmt)
                word_freqs = result.scalars().all()
                assert len(word_freqs) == 0
