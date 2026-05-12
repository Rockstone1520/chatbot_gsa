"""
sync_service.py

Sincroniza un producto entre Cosmos DB y Azure AI Search.
Se llama desde los endpoints CRUD DESPUÉS de modificar Cosmos,
dentro de la misma request HTTP — sin servicios adicionales.

Manejo de Free Tier de AI Search:
  El Free Tier tiene límite de 50 MB de almacenamiento y
  10,000 documentos. Si se alcanza el límite, la operación
  de indexación falla con un error 429 o 507. En ese caso
  retornamos un mensaje claro en lugar de romper el endpoint.
"""

import hashlib
from azure.core.exceptions import HttpResponseError
from config import get_openai_client, get_search_client, get_settings
from models.producto import SyncResult


SEARCH_FIELDS = [
    "id", "nombre", "marca", "categoria",
    "precio", "moneda", "stock", "descripcion",
]

FREE_TIER_ERRORS = {
    429: "Límite de rate limit de AI Search alcanzado. El producto fue guardado en Cosmos pero el índice no se actualizó. Reintenta en unos segundos.",
    507: "El índice de AI Search alcanzó el límite de almacenamiento del Free Tier (50 MB / 10k docs). El producto fue guardado en Cosmos. Para indexarlo, elimina documentos del índice o actualiza el tier.",
    403: "Sin permisos para escribir en AI Search. Verifica la API Key.",
}


def _construir_texto_embedding(producto: dict) -> str:
    return (
        f"{producto['nombre']}. "
        f"{producto['descripcion']}. "
        f"Marca: {producto['marca']}. "
        f"Categoría: {producto['categoria']}."
    )


def _generar_embedding(texto: str) -> list[float]:
    client = get_openai_client()
    s = get_settings()
    response = client.embeddings.create(
        input=texto,
        model=s.azure_openai_embedding_deployment,
    )
    return response.data[0].embedding


def _intentar_operacion_search(operacion: dict) -> SyncResult:
    """
    Ejecuta una operación sobre AI Search y maneja errores de Free Tier
    retornando un SyncResult descriptivo en lugar de lanzar excepción.
    """
    try:
        get_search_client().upload_documents([operacion])
        return SyncResult(
            cosmos_ok=True,
            search_ok=True,
            search_mensaje="Índice actualizado correctamente.",
            operacion=operacion["@search.action"],
        )
    except HttpResponseError as e:
        mensaje = FREE_TIER_ERRORS.get(
            e.status_code,
            f"Error inesperado al actualizar el índice ({e.status_code}): {e.message}",
        )
        return SyncResult(
            cosmos_ok=True,
            search_ok=False,
            search_mensaje=mensaje,
            operacion=operacion["@search.action"],
        )
    except Exception as e:
        return SyncResult(
            cosmos_ok=True,
            search_ok=False,
            search_mensaje=f"El índice no pudo actualizarse: {str(e)}",
            operacion=operacion["@search.action"],
        )


def sync_crear(producto: dict) -> SyncResult:
    """Indexa un producto nuevo: genera embedding + upload completo."""
    texto = _construir_texto_embedding(producto)
    vector = _generar_embedding(texto)

    doc = {
        "@search.action": "upload",
        **{k: producto[k] for k in SEARCH_FIELDS if k in producto},
        "precio":    float(producto["precio"]),
        "stock":     bool(producto["stock"]),
        "embedding": vector,
    }
    return _intentar_operacion_search(doc)


def sync_actualizar(producto_actualizado: dict, producto_anterior: dict) -> SyncResult:
    """
    Actualización inteligente:
    - Si cambió nombre o descripción → regenera embedding (merge completo)
    - Si solo cambió precio o stock  → merge solo metadata (sin costo de embedding)
    - Si no cambió nada relevante    → no hace nada
    """
    def _hash(p):
        return hashlib.md5(
            f"{p['nombre']}|{p['descripcion']}".encode()
        ).hexdigest()

    cambio_semantico = _hash(producto_actualizado) != _hash(producto_anterior)

    if cambio_semantico:
        texto = _construir_texto_embedding(producto_actualizado)
        vector = _generar_embedding(texto)
        doc = {
            "@search.action": "mergeOrUpload",
            **{k: producto_actualizado[k] for k in SEARCH_FIELDS if k in producto_actualizado},
            "precio":    float(producto_actualizado["precio"]),
            "stock":     bool(producto_actualizado["stock"]),
            "embedding": vector,
        }
    else:
        # Solo metadata — no consume tokens de embedding
        doc = {
            "@search.action": "merge",
            "id":     producto_actualizado["id"],
            "precio": float(producto_actualizado["precio"]),
            "stock":  bool(producto_actualizado["stock"]),
        }

    return _intentar_operacion_search(doc)


def sync_eliminar(producto_id: str) -> SyncResult:
    """Elimina un documento del índice por id."""
    doc = {"@search.action": "delete", "id": producto_id}
    return _intentar_operacion_search(doc)
