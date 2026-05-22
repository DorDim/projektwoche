"""SQLAlchemy-Initialisierung fuer Engine und Sessions der FastAPI-App."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from server.config import settings

database_url = settings.normalized_database_url
# Pool-Parameter sind absichtlich ueber Env steuerbar (lokal, VM, Cloud unterschiedlich).
engine_kwargs = {
    "pool_pre_ping": True,
    "pool_size": settings.db_pool_size,
    "max_overflow": settings.db_max_overflow,
}

engine = create_engine(database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    """FastAPI-Dependency: liefert pro Request eine DB-Session und schliesst sie sauber."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
