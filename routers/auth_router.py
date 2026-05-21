from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from auth import get_user, verify_password, create_access_token, hash_password
from models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

@router.post("/login")
def login(                                          # 👈 sin async
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = get_user(form.username, db)
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )
    token = create_access_token(user.username)
    return {"access_token": token, "token_type": "bearer"}

@router.post("/register")
def register(                                       # 👈 sin async
    body: RegisterRequest,
    db: Session = Depends(get_db)
):
    existing = get_user(body.username, db)
    if existing:
        raise HTTPException(status_code=400, detail="El usuario ya existe")

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    return {"message": "Usuario creado correctamente"}