from fastapi import APIRouter, HTTPException
from models.producto import ChatRequest, ChatResponse
from services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(body: ChatRequest):
    """
    Recibe una pregunta en lenguaje natural y devuelve una respuesta
    basada en el catálogo de productos indexado en Azure AI Search.

    Si la pregunta no está relacionada con productos o precios,
    retorna un mensaje indicando que el asistente está limitado
    al catálogo.
    """
    try:
        id_ultimo_response = body.id_ultimo_response if body.id_ultimo_response else None
        return chat_service.responder(
            pregunta=body.pregunta,
            id_ultimo_response=id_ultimo_response
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
