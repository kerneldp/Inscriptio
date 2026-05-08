from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from settings import settings

DATABASE_URL = settings.database_url

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def ensure_schema():
    """
    Lightweight schema migration for the demo SQLite DB.
    `Base.metadata.create_all()` does not add new columns to existing tables.
    """
    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(reports)")).fetchall()]
        if "session_date" not in cols:
            conn.execute(text("ALTER TABLE reports ADD COLUMN session_date TEXT"))
            conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()