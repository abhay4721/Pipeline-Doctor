import hashlib
import hmac
import json


def test_health_is_available_without_api_token(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_api_requires_bearer_token(client):
    response = client.get("/api/v1/stats")
    assert response.status_code == 401


def test_stats_accepts_valid_bearer_token(client):
    response = client.get("/api/v1/stats", headers={"Authorization": "Bearer test-api-token-with-sufficient-length"})
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_signed_webhook_deduplicates_delivery(client):
    payload = json.dumps({"action": "completed"}).encode()
    signature = hmac.new(b"test-webhook-secret", payload, hashlib.sha256).hexdigest()
    headers = {"X-Hub-Signature-256": f"sha256={signature}", "X-GitHub-Event": "ping", "X-GitHub-Delivery": "delivery-test-1"}
    first = client.post("/api/v1/webhooks/github", content=payload, headers=headers)
    second = client.post("/api/v1/webhooks/github", content=payload, headers=headers)
    assert first.status_code == 202
    assert first.json()["status"] == "ignored"
    assert second.status_code == 202
    assert second.json()["status"] == "duplicate"
