from azure.search.documents.models import VectorizedQuery
from config import get_openai_client, get_search_client, get_settings


def _embedding(texto: str) -> list[float]:
    s = get_settings()
    resp = get_openai_client().embeddings.create(
        input=texto,
        model=s.azure_openai_embedding_deployment,
    )
    return resp.data[0].embedding


def buscar_productos(
    pregunta: str,
    top_k: int = 5,
    marca: str = None,
    categoria: str = None,
    solo_en_stock: bool = False,
) -> list[dict]:
    """Búsqueda híbrida: semántica + keyword + filtros OData opcionales."""
    vector = _embedding(pregunta)

    vq = VectorizedQuery(
        vector=vector,
        k_nearest_neighbors=top_k,
        fields="embedding",
    )

    partes_filtro = []
    if marca:
        partes_filtro.append(f"marca eq '{marca}'")
    if categoria:
        partes_filtro.append(f"categoria eq '{categoria}'")
    if solo_en_stock:
        partes_filtro.append("stock eq true")
    filtro = " and ".join(partes_filtro) or None

    resultados = get_search_client().search(
        search_text=pregunta,
        vector_queries=[vq],
        filter=filtro,
        select=["id", "nombre", "marca", "categoria",
                "precio", "moneda", "stock", "descripcion"],
        top=top_k,
    )

    return [
        {
            "id":          r["id"],
            "nombre":      r["nombre"],
            "marca":       r["marca"],
            "categoria":   r["categoria"],
            "precio":      r["precio"],
            "moneda":      r["moneda"],
            "stock":       r["stock"],
            "descripcion": r["descripcion"],
            "score":       r["@search.score"],
        }
        for r in resultados
    ]


def formatear_contexto(productos: list[dict]) -> str:
    bloques = []
    for p in productos:
        disponibilidad = "En stock" if p["stock"] else "Sin stock"
        bloques.append(
            f"Producto: {p['nombre']}\n"
            f"Marca: {p['marca']} | Categoría: {p['categoria']}\n"
            f"Precio: {p['moneda']} {p['precio']:.2f}\n"
            f"Disponibilidad: {disponibilidad}\n"
            f"Descripción: {p['descripcion']}"
        )
    return "\n---\n".join(bloques)
