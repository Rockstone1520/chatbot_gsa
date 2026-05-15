import uuid
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosHttpResponseError
from config import get_cosmos_container
from models.producto import ProductoCreate, ProductoUpdate


def _container():
    return get_cosmos_container()


def crear_producto(data: ProductoCreate) -> dict:
    """Inserta un producto nuevo en Cosmos. Genera el id y fija pk=id."""
    producto = data.model_dump()
    producto["id"] = f"prod-{uuid.uuid4().hex[:8]}"
    producto["pk"] = producto["id"]
    _container().create_item(body=producto)
    return producto


def obtener_producto(producto_id: str) -> dict | None:
    """Obtiene un producto por id. Retorna None si no existe."""
    try:
        return _container().read_item(item=producto_id, partition_key=producto_id)
    except CosmosResourceNotFoundError:
        return None


def actualizar_producto(producto_id: str, data: ProductoUpdate) -> dict | None:
    """
    Actualiza solo los campos enviados (patch parcial).
    Retorna el documento actualizado o None si no existe.
    """
    existente = obtener_producto(producto_id)
    if not existente:
        return None

    cambios = data.model_dump(exclude_none=True)
    existente.update(cambios)
    _container().replace_item(item=producto_id, body=existente)
    return existente


def eliminar_producto(producto_id: str) -> bool:
    """Elimina un producto. Retorna True si existía, False si no."""
    try:
        _container().delete_item(item=producto_id, partition_key=producto_id)
        return True
    except CosmosResourceNotFoundError:
        return False


def listar_productos(categoria: str = None, marca: str = None) -> list[dict]:
    """Lista todos los productos con filtros opcionales."""
    condiciones = []
    params = []

    if categoria:
        condiciones.append("c.categoria = @categoria")
        params.append({"name": "@categoria", "value": categoria})
    if marca:
        condiciones.append("c.marca = @marca")
        params.append({"name": "@marca", "value": marca})

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    query = f"SELECT * FROM c {where} ORDER BY c.nombre"

    return list(_container().query_items(
        query=query,
        parameters=params if params else None,
        enable_cross_partition_query=True,
    ))
