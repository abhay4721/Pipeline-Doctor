import os
import sys
import tempfile
from pathlib import Path

test_db = tempfile.NamedTemporaryFile(prefix="pipeline-doctor-test-", suffix=".db", delete=False)
test_db.close()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///" + test_db.name
os.environ["API_TOKEN"] = "test-api-token-with-sufficient-length"
os.environ["GITHUB_WEBHOOK_SECRET"] = "test-webhook-secret"
os.environ["ENVIRONMENT"] = "test"

import pytest
from fastapi.testclient import TestClient
from app.db import Base, engine
from app.main import app

Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
