"""
database.py — SQLAlchemy connection setup.

Using SQLite for local development: zero setup, single file
(safebrowse.db), no server to install/run. When you deploy to cPanel
(which gives you MySQL), the only change needed is DATABASE_URL below —
everything else (models.py, auth.py, the endpoints) stays identical,
since SQLAlchemy abstracts the actual database engine.

To switch to MySQL later:
    DATABASE_URL = "mysql+pymysql://username:password@localhost/safebrowse"
(and `pip install pymysql`)
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./safebrowse.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session, closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()