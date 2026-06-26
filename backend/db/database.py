# backend/db/database.py

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/creditlens")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={"connect_timeout": 10}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_engine():
    return engine


def get_connection():
    return engine.connect()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(schema_path: str = None):
    if schema_path is None:
        base = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(base, "schema.sql")
    with open(schema_path, "r") as f:
        ddl = f.read()
    with engine.connect() as conn:
        conn.execute(text(ddl))
        conn.commit()


def test_connection():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            return result.fetchone()[0] == 1
    except Exception as e:
        print(f"DB connection failed: {e}")
        return False