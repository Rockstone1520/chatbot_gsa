from pydantic import BaseModel, Field
from typing import Optional


class ProductoBase(BaseModel):
    nombre: str
    marca: str
    categoria: str
    precio: float = Field(gt=0)
    moneda: str = "PEN"
    stock: bool = True
    descripcion: str


class ProductoCreate(ProductoBase):
    """Body para POST /productos — el id lo genera el backend."""
    pass


class ProductoUpdate(BaseModel):
    """Body para PUT /productos/{id} — todos los campos son opcionales."""
    nombre: Optional[str] = None
    marca: Optional[str] = None
    categoria: Optional[str] = None
    precio: Optional[float] = Field(default=None, gt=0)
    moneda: Optional[str] = None
    stock: Optional[bool] = None
    descripcion: Optional[str] = None


class ProductoResponse(ProductoBase):
    """Respuesta con id incluido."""
    id: str

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    pregunta: str = Field(min_length=1, max_length=500)


class ChatResponse(BaseModel):
    respuesta: str
    productos_encontrados: int
    fuentes: list[str] = []
    es_fuera_de_tema: bool = False


class SyncResult(BaseModel):
    cosmos_ok: bool
    search_ok: bool
    search_mensaje: str
    operacion: str
