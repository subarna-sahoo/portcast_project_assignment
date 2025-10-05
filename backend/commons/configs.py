from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# Constants
TOP_N_CACHED_WORDS = 10  # Number of top frequency words to keep in Redis cache

# Redis Cache Keys
REDIS_TOP_WORDS_KEY = "top_words_freq"  # Key for storing top N word frequencies
REDIS_DEFINITION_PREFIX = "word_def:"  # Prefix for word definition cache

# Redis TTL values (in seconds)
REDIS_WORD_FREQ_TTL = 7 * 24 * 60 * 60  # 7 days for word frequencies
REDIS_DEFINITION_TTL = 60 * 60  # 1 hour for definitions


class Settings(BaseSettings):
    # Database
    database_url: str

    # Elasticsearch 
    elasticsearch_url: str

    # Redis
    redis_url: str

    # Dictionary API
    dictionary_api_url: str #"https://api.dictionaryapi.dev/api/v2/entries/en"

    # Metaphorpsum API
    metaphorpsum_url: str #"http://metaphorpsum.com/paragraphs/1"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
