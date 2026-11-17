from app.services.analyzer import local_analysis, sanitize_log


def test_secret_redaction():
    result = sanitize_log("token=ghp_abcdefghijklmnopqrstuvwxyz0123456789\nAuthorization: Bearer abc.def\npostgres://worker:private-pass@db.example/app\nAKIA1234567890ABCDEF")
    assert "ghp_" not in result
    assert "abc.def" not in result
    assert "private-pass" not in result
    assert "AKIA1234567890ABCDEF" not in result
    assert "[REDACTED]" in result


def test_analyzer_uses_log_evidence():
    log = "Step: install\nERROR: No matching distribution found for example"
    result = local_analysis(log)
    assert result["failure_type"] == "dependency_error"
    assert result["evidence"] == ["ERROR: No matching distribution found for example"]
    assert result["confidence"] > 0


def test_unknown_failure_is_uncertain():
    result = local_analysis("Process exited with code 1")
    assert result["failure_type"] == "unknown"
    assert result["confidence"] <= 0.35
    assert result["evidence"] == []
