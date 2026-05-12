from functools import lru_cache
from pydantic_settings import BaseSettings
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.cosmos import CosmosClient
from azure.core.credentials import AzureKeyCredential


class Settings(BaseSettings):
    # Azure OpenAI
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_api_version: str = "2024-02-01"
    azure_openai_embedding_deployment: str
    azure_openai_chat_deployment: str

    # Azure AI Search
    azure_search_endpoint: str
    azure_search_api_key: str
    azure_search_index_name: str = "catalogo-productos"

    # Cosmos DB
    cosmos_endpoint: str
    cosmos_key: str
    cosmos_database: str = "catalogo_db"
    cosmos_container: str = "productos"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_openai_client() -> AzureOpenAI:
    s = get_settings()
    return AzureOpenAI(
        azure_endpoint=s.azure_openai_endpoint,
        api_key=s.azure_openai_api_key,
        api_version=s.azure_openai_api_version,
    )


def get_search_client() -> SearchClient:
    s = get_settings()
    return SearchClient(
        endpoint=s.azure_search_endpoint,
        index_name=s.azure_search_index_name,
        credential=AzureKeyCredential(s.azure_search_api_key),
    )


def get_index_client() -> SearchIndexClient:
    s = get_settings()
    return SearchIndexClient(
        endpoint=s.azure_search_endpoint,
        credential=AzureKeyCredential(s.azure_search_api_key),
    )


def get_cosmos_container():
    s = get_settings()
    client = CosmosClient(url=s.cosmos_endpoint, credential=s.cosmos_key)
    db = client.get_database_client(s.cosmos_database)
    return db.get_container_client(s.cosmos_container)
