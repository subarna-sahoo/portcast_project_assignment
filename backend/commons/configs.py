from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# Constants
TOP_N_CACHED_WORDS = 100  # Number of top frequency words to keep in Redis cache


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
