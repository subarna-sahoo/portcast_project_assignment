import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import Response
from backend.commons.models import WordFrequency


class TestDictionaryAPI:
    """Test cases for the /dictionary endpoint"""

    @pytest.mark.asyncio
    async def test_get_dictionary_success_with_cache(self, client, mock_redis, test_db, sample_word_frequencies):
        """Test successful retrieval of dictionary with cached data"""
        # Mock Redis to return cached word frequencies
        mock_redis.zrevrange = AsyncMock(return_value=[
            b"test:100", b"sample:80", b"paragraph:60", b"words:50", b"data:40"
        ])

        # Mock Redis to return cached definitions
        async def mock_get(key):
            definitions = {
                "definition:test": b"A procedure for critical evaluation",
                "definition:sample": b"A small part or quantity",
                "definition:paragraph": b"A distinct section of writing",
                "definition:words": b"A unit of language",
                "definition:data": b"Facts and statistics"
            }
            return definitions.get(key)

        mock_redis.get = AsyncMock(side_effect=mock_get)

        # Make request
        response = await client.get("/api/dictionary")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "definitions" in data
        assert len(data["definitions"]) == 5
        assert data["definitions"][0]["word"] == "test"
        assert data["definitions"][0]["frequency"] == 100
        assert data["definitions"][0]["definition"] == "A procedure for critical evaluation"

    @pytest.mark.asyncio
    async def test_get_dictionary_success_from_db(self, client, mock_redis, test_db):
        """Test successful retrieval of dictionary from database when cache misses"""
        # Setup: Add word frequencies to test database
        word_freq = WordFrequency(word="test", frequency=100)
        test_db.add(word_freq)
        await test_db.commit()

        # Mock Redis to return no cached word frequencies
        mock_redis.zrevrange = AsyncMock(return_value=[])
        mock_redis.get = AsyncMock(return_value=None)

        # Mock the httpx client for external API call
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock(spec=Response)
            mock_response.json.return_value = [{
                "meanings": [{
                    "definitions": [{
                        "definition": "A procedure for critical evaluation"
                    }]
                }]
            }]
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Make request
            response = await client.get("/api/dictionary")

            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert "definitions" in data
            assert len(data["definitions"]) == 1
            assert data["definitions"][0]["word"] == "test"
            assert data["definitions"][0]["frequency"] == 100
            assert data["definitions"][0]["definition"] == "A procedure for critical evaluation"

    @pytest.mark.asyncio
    async def test_get_dictionary_external_api_failure(self, client, mock_redis, test_db):
        """Test dictionary endpoint when external API fails"""
        # Setup: Add word frequency to test database
        word_freq = WordFrequency(word="test", frequency=100)
        test_db.add(word_freq)
        await test_db.commit()

        # Mock Redis cache misses
        mock_redis.zrevrange = AsyncMock(return_value=[])
        mock_redis.get = AsyncMock(return_value=None)

        # Mock the httpx client to raise an exception
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("API Error"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Make request
            response = await client.get("/api/dictionary")

            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert len(data["definitions"]) == 1
            assert data["definitions"][0]["definition"] == "Definition not found"

    @pytest.mark.asyncio
    async def test_get_dictionary_no_words_in_database(self, client, mock_redis, test_db):
        """Test dictionary endpoint when no words exist in database"""
        # Mock Redis cache misses
        mock_redis.zrevrange = AsyncMock(return_value=[])

        # Make request
        response = await client.get("/api/dictionary")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "definitions" in data
        assert len(data["definitions"]) == 0

    @pytest.mark.asyncio
    async def test_get_dictionary_redis_failure_fallback_to_db(self, client, mock_redis, test_db):
        """Test dictionary endpoint when Redis fails but DB works"""
        # Setup: Add word frequency to test database
        word_freq = WordFrequency(word="fallback", frequency=75)
        test_db.add(word_freq)
        await test_db.commit()

        # Mock Redis to fail
        mock_redis.zrevrange = AsyncMock(side_effect=Exception("Redis connection error"))
        mock_redis.get = AsyncMock(side_effect=Exception("Redis connection error"))

        # Mock the httpx client for external API call
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock(spec=Response)
            mock_response.json.return_value = [{
                "meanings": [{
                    "definitions": [{
                        "definition": "A backup option"
                    }]
                }]
            }]
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Make request
            response = await client.get("/api/dictionary")

            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert len(data["definitions"]) == 1
            assert data["definitions"][0]["word"] == "fallback"

    @pytest.mark.asyncio
    async def test_get_dictionary_caches_definition(self, client, mock_redis, test_db):
        """Test that dictionary endpoint caches fetched definitions"""
        # Setup: Add word frequency to test database
        word_freq = WordFrequency(word="cache", frequency=90)
        test_db.add(word_freq)
        await test_db.commit()

        # Mock Redis cache misses
        mock_redis.zrevrange = AsyncMock(return_value=[])
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock(return_value=True)

        # Mock the httpx client for external API call
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock(spec=Response)
            mock_response.json.return_value = [{
                "meanings": [{
                    "definitions": [{
                        "definition": "A storage location"
                    }]
                }]
            }]
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Make request
            response = await client.get("/api/dictionary")

            # Assertions
            assert response.status_code == 200
            # Verify that setex was called to cache the definition
            mock_redis.setex.assert_called()

    @pytest.mark.asyncio
    async def test_get_dictionary_malformed_api_response(self, client, mock_redis, test_db):
        """Test dictionary endpoint handles malformed API responses"""
        # Setup: Add word frequency to test database
        word_freq = WordFrequency(word="malformed", frequency=55)
        test_db.add(word_freq)
        await test_db.commit()

        # Mock Redis cache misses
        mock_redis.zrevrange = AsyncMock(return_value=[])
        mock_redis.get = AsyncMock(return_value=None)

        # Mock the httpx client with malformed response
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock(spec=Response)
            mock_response.json.return_value = {"error": "Invalid word"}  # Malformed structure
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Make request
            response = await client.get("/api/dictionary")

            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["definitions"][0]["definition"] == "Definition not found"

    @pytest.mark.asyncio
    async def test_get_dictionary_top_10_limit(self, client, mock_redis, test_db):
        """Test that dictionary endpoint returns only top 10 words by default"""
        # Setup: Add 15 word frequencies to test database
        for i in range(15):
            word_freq = WordFrequency(word=f"word{i}", frequency=100-i)
            test_db.add(word_freq)
        await test_db.commit()

        # Mock Redis cache misses
        mock_redis.zrevrange = AsyncMock(return_value=[])
        mock_redis.get = AsyncMock(return_value=None)

        # Mock the httpx client for external API call
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock(spec=Response)
            mock_response.json.return_value = [{
                "meanings": [{
                    "definitions": [{
                        "definition": "Test definition"
                    }]
                }]
            }]
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Make request
            response = await client.get("/api/dictionary")

            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert len(data["definitions"]) == 10  # Should only return top 10

    @pytest.mark.asyncio
    async def test_get_dictionary_cache_bytes_decoding(self, client, mock_redis, test_db):
        """Test that dictionary endpoint properly decodes bytes from Redis"""
        # Mock Redis to return cached word frequencies
        mock_redis.zrevrange = AsyncMock(return_value=[b"decode:50"])

        # Mock Redis to return bytes definition
        mock_redis.get = AsyncMock(return_value=b"A process of conversion")

        # Make request
        response = await client.get("/api/dictionary")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data["definitions"]) == 1
        assert data["definitions"][0]["definition"] == "A process of conversion"
