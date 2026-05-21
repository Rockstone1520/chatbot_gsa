from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import get_settings

def get_engine():
    s = get_settings()
    url = (
        f"mssql+pymssql://{s.azure_sql_user}:{s.azure_sql_password}"
        f"@{s.azure_sql_server}:1433/{s.azure_sql_database}"
        f"?charset=utf8"
    )
    return create_engine(url, echo=False)

engine = get_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()