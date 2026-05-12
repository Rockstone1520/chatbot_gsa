from fastapi import APIRouter, HTTPException, Query
from models.producto import (
    ProductoCreate, ProductoUpdate, ProductoResponse, SyncResult
)
from services import cosmos_service, sync_service

router = APIRouter(prefix="/productos", tags=["productos"])


@router.post("", response_model=dict, status_code=201)
def crear_producto(body: ProductoCreate):
    """
    Crea un producto en Cosmos DB e intenta indexarlo en AI Search.
    Si AI Search falla (Free Tier lleno, rate limit, etc.) el producto
    queda en Cosmos y la respuesta incluye el detalle del error.
    """
    producto = cosmos_service.crear_producto(body)
    sync = sync_service.sync_crear(producto)

    return {
        "producto": ProductoResponse(**producto),
        "sync":     sync,
    }


@router.get("", response_model=list[ProductoResponse])
def listar_productos(
    categoria: str = Query(default=None),
    marca:     str = Query(default=None),
):
    """Lista productos desde Cosmos DB con filtros opcionales."""
    return cosmos_service.listar_productos(categoria=categoria, marca=marca)


@router.get("/{producto_id}", response_model=ProductoResponse)
def obtener_producto(producto_id: str):
    """Obtiene un producto por id desde Cosmos DB."""
    producto = cosmos_service.obtener_producto(producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.put("/{producto_id}", response_model=dict)
def actualizar_producto(producto_id: str, body: ProductoUpdate):
    """
    Actualiza un producto en Cosmos DB y sincroniza AI Search.

    Sync inteligente:
    - Si cambió nombre o descripción → regenera embedding
    - Si solo cambió precio o stock  → merge sin regenerar embedding
    """
    anterior = cosmos_service.obtener_producto(producto_id)
    if not anterior:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    actualizado = cosmos_service.actualizar_producto(producto_id, body)
    sync = sync_service.sync_actualizar(actualizado, anterior)

    return {
        "producto": ProductoResponse(**actualizado),
        "sync":     sync,
    }


@router.delete("/{producto_id}", response_model=dict)
def eliminar_producto(producto_id: str):
    """
    Elimina un producto de Cosmos DB y lo quita del índice de AI Search.
    """
    eliminado = cosmos_service.eliminar_producto(producto_id)
    if not eliminado:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    sync = sync_service.sync_eliminar(producto_id)

    return {
        "mensaje": f"Producto {producto_id} eliminado de Cosmos DB.",
        "sync":    sync,
    }
