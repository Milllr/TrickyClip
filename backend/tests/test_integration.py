import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.db import get_session
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

# create in-memory test database
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_health_check(client):
    """test basic health endpoint"""
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_readiness_check(client):
    """test readiness endpoint"""
    response = client.get("/health/ready")
    assert response.status_code == 200


def test_list_people(client):
    """test people endpoint"""
    response = client.get("/api/people/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_tricks(client):
    """test tricks endpoint"""
    response = client.get("/api/tricks/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_clips(client):
    """test clips listing"""
    response = client.get("/api/clips/")
    assert response.status_code == 200
    data = response.json()
    assert "clips" in data
    assert "total" in data


def test_clip_stats(client):
    """test clip statistics"""
    response = client.get("/api/clips/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_clips" in data
    assert "by_year" in data


def test_jobs_list(client):
    """test jobs endpoint"""
    response = client.get("/api/jobs/")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "running" in data


def test_storage_stats(client):
    """test storage stats"""
    response = client.get("/api/admin/storage")
    assert response.status_code == 200
    data = response.json()
    assert "total_gb" in data


