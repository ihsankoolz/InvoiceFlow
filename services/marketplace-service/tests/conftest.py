import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

# Add repo root to path so `shared` package is importable when running pytest
# from services/marketplace-service/ (shared/ lives at the repo root)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


SQLITE_URL = "sqlite:///:memory:"

engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def db():
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
