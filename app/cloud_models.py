import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Integer, Float, ForeignKey, Text, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import inspect as sa_inspect


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
    method = Column(String(10), nullable=True)
    status_code = Column(Integer, nullable=False)
    duration_ms = Column(Float, nullable=False)
    request_body = Column(Text, nullable=True)
    response_body = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_logs()


def _migrate_logs():
    inspector = sa_inspect(engine)
    columns = [c["name"] for c in inspector.get_columns("logs")]
    migrates = [
        ("method", "VARCHAR(10)"),
        ("request_body", "TEXT"),
        ("response_body", "TEXT"),
    ]
    for col_name, col_type in migrates:
        if col_name not in columns:
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE logs ADD COLUMN {col_name} {col_type}"))
                conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
