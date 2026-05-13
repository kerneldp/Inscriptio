from sqlalchemy import create_engine, text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from settings import settings

DATABASE_URL = settings.database_url

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def migrate_schema():
    """
    Add Report columns introduced after the initial schema (SQLite + MySQL).
    CREATE TABLE from ORM does not ALTER existing production tables.
    """
    insp = inspect(engine)
    if "reports" not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns("reports")}
    dialect = engine.dialect.name

    bool_add = (
        "ALTER TABLE reports ADD COLUMN urgent_review INTEGER NOT NULL DEFAULT 0"
        if dialect == "sqlite"
        else "ALTER TABLE reports ADD COLUMN urgent_review TINYINT(1) NOT NULL DEFAULT 0"
    )

    alters = []
    if "educator_context" not in existing:
        alters.append(
            "ALTER TABLE reports ADD COLUMN educator_context TEXT"
            if dialect == "sqlite"
            else "ALTER TABLE reports ADD COLUMN educator_context TEXT NULL"
        )
    if "urgent_review" not in existing:
        alters.append(bool_add)
    if "clinician_notes" not in existing:
        alters.append(
            "ALTER TABLE reports ADD COLUMN clinician_notes TEXT"
            if dialect == "sqlite"
            else "ALTER TABLE reports ADD COLUMN clinician_notes TEXT NULL"
        )
    if "override_category" not in existing:
        alters.append(
            "ALTER TABLE reports ADD COLUMN override_category VARCHAR(120)"
            if dialect == "sqlite"
            else "ALTER TABLE reports ADD COLUMN override_category VARCHAR(120) NULL"
        )
    if not alters:
        return

    with engine.begin() as conn:
        for stmt in alters:
            conn.execute(text(stmt))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
