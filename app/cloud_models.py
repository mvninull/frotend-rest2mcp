import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Integer, Float, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///cloud.db")


class Base(DeclarativeBase):
    pass


class ServerDB(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(String(50), unique=True, nullable=False, index=True)
    apikey = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    spec_url = Column(String(500), nullable=False)
    spec_data = Column(Text, nullable=True)
    target_url = Column(String(500), nullable=True)
    transport = Column(String(10), default="http")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class LogDB(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(String(50), nullable=False, index=True)
    tool_called = Column(String(200), nullable=False)
    status_code = Column(Integer, nullable=False)
    duration_ms = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
