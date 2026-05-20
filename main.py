from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from azure.search.documents.indexes.models import (
    SearchIndex, SearchFieldDataType, SimpleField,
    SearchableField, VectorSearch,
    HnswAlgorithmConfiguration, VectorSearchProfile,
    SearchField as VectorField,
)
from config import get_index_client, get_settings
from routers import chat, productos
from security import verify_api_key


def _crear_indice_si_no_existe():
    """Crea el índice vectorial en AI Search al arrancar si no existe."""
    s = get_settings()
    client = get_index_client()

    try:
        client.get_index(s.azure_search_index_name)
        return  # ya existe
    except Exception:
        pass  # no existe, lo creamos

    campos = [
        SimpleField(name="id",       type=SearchFieldDataType.String, key=True),
        SearchableField(name="nombre",      type=SearchFieldDataType.String),
        SearchableField(name="descripcion", type=SearchFieldDataType.String),
        SimpleField(name="marca",     type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="categoria", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="precio",    type=SearchFieldDataType.Double,  filterable=True, sortable=True),
        SimpleField(name="moneda",    type=SearchFieldDataType.String),
        SimpleField(name="stock",     type=SearchFieldDataType.Boolean, filterable=True),
        VectorField(
            name="embedding",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name="perfil-hnsw",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw")],
        profiles=[VectorSearchProfile(name="perfil-hnsw", algorithm_configuration_name="hnsw")],
    )

    client.create_or_update_index(
        SearchIndex(name=s.azure_search_index_name, fields=campos, vector_search=vector_search)
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: crea el índice si no existe
    _crear_indice_si_no_existe()
    yield
    # Shutdown: nada que limpiar


app = FastAPI(
    title="Catálogo RAG API",
    description="Backend RAG sobre catálogo de productos de GSA con Azure.",
    version="1.0.0",
    lifespan=lifespan,
    dependencies=[Depends(verify_api_key)]
)

app.include_router(chat.router)
app.include_router(productos.router)


@app.get("/health", tags=["infra"])
def health():
    """Liveness probe para Azure Container Apps."""
    return {"status": "ok"}


@app.get("/", tags=["infra"])
def root():
    return {
        "mensaje": "Catálogo RAG API",
        "docs":    "/docs",
        "health":  "/health",
    }
