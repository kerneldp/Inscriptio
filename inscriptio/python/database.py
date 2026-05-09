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
    new_cols = {
        "session_date":       "TEXT",
        "severe_anomaly_img": "TEXT",
        "patch_scores":       "TEXT",
        "findings":           "TEXT",
    }
    with engine.connect() as conn:
        existing = [row[1] for row in conn.execute(text("PRAGMA table_info(reports)")).fetchall()]
        for col, col_type in new_cols.items():
            if col not in existing:
                conn.execute(text(f"ALTER TABLE reports ADD COLUMN {col} {col_type}"))
        conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()