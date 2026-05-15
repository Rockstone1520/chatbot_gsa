"""
chat_service.py

Pipeline RAG completo con dos capas de guardrail:

1. Clasificador de tema: antes de buscar, determina si la pregunta
   es sobre productos/precios. Si no lo es, retorna el mensaje
   default sin consumir tokens de búsqueda ni de generación.

2. Prompt restrictivo: instruye al LLM para que solo use el
   contexto y no invente precios.
"""

import json
from typing import Optional
from config import get_openai_client, get_settings
from .search_service import buscar_productos, formatear_contexto
from models.producto import ChatResponse


MENSAJE_FUERA_DE_TEMA = (
    "Soy un asistente especializado en el catálogo de productos. "
    "Solo puedo responder preguntas sobre productos, precios y disponibilidad. "
    "Para otro tipo de consultas, por favor contacta a nuestro equipo de soporte."
)

SYSTEM_PROMPT = """
    Eres un asistente de ventas especializado en electrónica.
    Tu única función es responder preguntas sobre productos del catálogo proporcionado.

    Reglas estrictas:
    1. Responde SOLO usando la información del CATÁLOGO proporcionado.
    2. SIEMPRE menciona el precio exacto del producto (en la moneda indicada).
    3. SIEMPRE indica si el producto está en stock o no.
    4. Si hay varios productos relevantes, prioriza el más exacto y menciona alternativas brevemente.
    5. Si no encuentras el producto exacto, sugiere el más similar del catálogo.
    6. NUNCA inventes precios ni disponibilidad — usa SOLO los datos del catálogo.
    7. Responde en español, de forma amigable y concisa.
    8. No hagas preguntas follow up solo da la respuesta.
    9. Cuando no hay un producto exacto entrega los resultados encontrados en formato de lista.

    Ejemplos:
    1.
    user: "Que televisores tenemos disponibles?"
    respuesta: "Contamos con estos televisores en stock:
        1. Televisor LG Nanocell de 50 pulgadas [Precio: S/234.00]
        2. Televisor Samsung OLED de 50 pulgadas [Precio: S/1,234.00]
    "
    2.
    user: "Cuanto esta el LG Nanocell de 50 pulg?"
    respuesta: " El televisor LG Nanocell de 50 pulgadas tiene un costo de S/1,234.00. Sin embargo, 
    no contamos con el stock de este producto."
"""


def _es_pregunta_de_catalogo(pregunta: str) -> bool:
    """
    Clasifica si la pregunta es sobre productos/precios del catálogo.
    Usa el LLM con temperatura 0 para máxima consistencia.
    Responde solo con JSON {"es_catalogo": true/false}.
    """
    s = get_settings()
    prompt = (
        'Determina si esta pregunta está relacionada con consultar productos, '
        'precios, disponibilidad o características de un catálogo de tienda.\n\n'
        f'Pregunta: "{pregunta}"\n\n'
        'Responde SOLO con JSON válido, sin texto adicional:\n'
        '{"es_catalogo": true}  o  {"es_catalogo": false}\n\n'
        'Ejemplos que son catálogo: precio de X, ¿tienen Y en stock?, '
        'características de Z, cuánto cuesta, qué televisores tienen.\n'
        'Ejemplos que NO son catálogo: cómo estás, chiste, receta, '
        'clima, política, historia, matemáticas.'
    )
    try:
        resp = get_openai_client().responses.create(
            model=s.azure_openai_chat_deployment,
            input=[{"role": "user", "content": prompt}],
            temperature=0,
            max_output_tokens=20,
        )
        raw = resp.output_text.strip()
        return json.loads(raw).get("es_catalogo", False)
    except Exception:
        # Si el clasificador falla, asumimos que es válida
        # para no bloquear preguntas legítimas
        return True


def responder(pregunta: str, id_ultimo_response: Optional[str] = None) -> ChatResponse:
    """Pipeline RAG completo con guardrail de tema."""

    # ── Guardrail: clasificación de tema ──────────────────────
    if not _es_pregunta_de_catalogo(pregunta):
        return ChatResponse(
            respuesta=MENSAJE_FUERA_DE_TEMA,
            productos_encontrados=0,
            fuentes=[],
            es_fuera_de_tema=True,
            id_response=None,
        )
    print("[STEP 1] Se termino con los guardrails")
    # ── Retrieval: búsqueda híbrida ───────────────────────────
    productos = buscar_productos(pregunta, top_k=5)

    print(f"[STEP 2] Productos encontrados: {productos}")

    if not productos:
        return ChatResponse(
            respuesta=(
                "No encontré productos que coincidan con tu búsqueda en el catálogo. "
                "Puedes intentar con otro término o preguntarme por una categoría específica."
            ),
            productos_encontrados=0,
            fuentes=[],
            es_fuera_de_tema=False,
            id_response=None,
        )

    # ── Generación: LLM con contexto ─────────────────────────
    contexto = formatear_contexto(productos)
    s = get_settings()

    print("[STEP 3] Se formateo el contexto")

    user_prompt = (
        f"CATÁLOGO DISPONIBLE:\n{contexto}\n\n"
        f"PREGUNTA DEL CLIENTE:\n{pregunta}"
    )

    resp = get_openai_client().responses.create(
        model=s.azure_openai_chat_deployment,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.2,
        max_output_tokens=600,
        previous_response_id=id_ultimo_response
    )

    print("[STEP 4] Se genero la ultima respuesta")


    return ChatResponse(
        respuesta=resp.output_text,
        productos_encontrados=len(productos),
        fuentes=list({p["nombre"] for p in productos}),
        es_fuera_de_tema=False,
        id_response=resp.id,
    )
