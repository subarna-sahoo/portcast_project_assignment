import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import Response
from backend.commons.models import WordFrequency


class TestDictionaryAPI:
    """Test cases for the /dictionary endpoint"""

    @pytest.mark.asyncio
    async def test_get_dictionary_success_with_cache(self, client, mock_redis, test_db, sample_word_frequencies):
        """Test successful retrieval of dictionary with cached data"""
        # Mock the get_top_words_from_cache function to return cached data
        cached_words = [
            ("test", 100), ("sample", 80), ("paragraph", 60), ("words", 50), ("data", 40),
            ("python", 30), ("fastapi", 25), ("redis", 20), ("database", 15), ("search", 10)
        ]

        definitions_map = {
            "word_def:test": b"A procedure for critical evaluation",
            "word_def:sample": b"A small part or quantity",
            "word_def:paragraph": b"A distinct section of writing",
            "word_def:words": b"A unit of language",
            "word_def:data": b"Facts and statistics",
            "word_def:python": b"A programming language",
            "word_def:fastapi": b"A modern web framework",
            "word_def:redis": b"An in-memory data store",
            "word_def:database": b"A structured data storage",
            "word_def:search": b"The act of looking for something"
        }

        async def mock_get(key):
            return definitions_map.get(key)

        mock_redis.get.side_effect = mock_get

        # Patch get_top_words_from_cache to return our cached data
        with patch('backend.dict_service.service.get_top_words_from_cache', new=AsyncMock(return_value=cached_words)):
            # Make request
            response = await client.get("/api/dictionary")

            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert "definitions" in data
            assert len(data["definitions"]) == 10  # API returns top 10 by default
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
        # Mock get_top_words_from_cache to return cached data
        cached_words = [
            ("decode", 50), ("word2", 45), ("word3", 40), ("word4", 35), ("word5", 30),
            ("word6", 25), ("word7", 20), ("word8", 15), ("word9", 10), ("word10", 5)
        ]

        async def mock_get(key):
            if key == "word_def:decode":
                return b"A process of conversion"
            return None

        mock_redis.get.side_effect = mock_get

        # Patch get_top_words_from_cache to return our cached data
        with patch('backend.dict_service.service.get_top_words_from_cache', new=AsyncMock(return_value=cached_words)):
            # Make request
            response = await client.get("/api/dictionary")

            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert len(data["definitions"]) == 10
            # Verify the first word "decode" has the cached definition decoded properly
            assert data["definitions"][0]["word"] == "decode"
            assert data["definitions"][0]["definition"] == "A process of conversion"
