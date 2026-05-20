from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from server.config import settings

database_url = settings.normalized_database_url
engine_kwargs = {
    "pool_pre_ping": True,
    "pool_size": settings.db_pool_size,
    "max_overflow": settings.db_max_overflow,
}

engine = create_engine(database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
