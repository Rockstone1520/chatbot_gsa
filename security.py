from fastapi import Security, HTTPException, status, Request
from fastapi.security import APIKeyHeader
from config import get_settings

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

PUBLIC_PATHS = {"/health", "/", "/docs", "/openapi.json"}

async def verify_api_key(request: Request, key: str = Security(api_key_header)):
    if request.url.path in PUBLIC_PATHS:
        return

    if key != get_settings().internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida o ausente"
        )