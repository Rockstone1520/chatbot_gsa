from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from datetime import datetime
from database import Base
import uuid

class User(Base):
    __tablename__ = "users"

    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)