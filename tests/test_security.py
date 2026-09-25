# 安全性：限流、reset-db 防護、錯誤訊息不外洩、CORS
import pytest

import Main
import heygen
import rate_limit

START = {"position": "後端工程師", "level": "新鮮人"}
SECRET = "SECRET-INTERNAL-XYZ"


# ---------- 限流 ----------
def test_rate_limit_returns_429_per_user(client, login, fake_ai, monkeypatch):
    monkeypatch.setitem(rate_limit.RATE_LIMITS, "interview_start", (3, 60))
    login("u1")
    codes = [client.post("/api/interview/start", json=START).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
    r = client.post("/api/interview/start", json=START)
    assert "操作太頻繁" in r.json()["detail"] and int(r.headers["Retry-After"]) > 0

    login("u2")  # 其他使用者不受影響
    assert client.post("/api/interview/start", json=START).status_code == 200
    login("u1")  # 讀取類端點不受限
    assert client.get("/api/interview/history").status_code == 200


@pytest.mark.parametrize("path", [
    "/api/interview/start", "/api/interview/chat", "/api/interview/finish", "/api/resume/parse",
    "/api/resume", "/chat", "/avatar/tts", "/heygen/embed",
])
def test_every_quota_spending_endpoint_is_rate_limited(path):
    """會花 AI / 語音 / HeyGen 額度的 POST 端點都必須掛 rate_limited()，新增端點時漏掛會在這裡被抓到。"""
    route = next(r for r in Main.app.routes if getattr(r, "path", None) == path and "POST" in r.methods)
    names = [getattr(d.call, "__qualname__", "") for d in route.dependant.dependencies]
    assert any("rate_limited" in n for n in names), names


# ---------- reset-db ----------
def test_reset_db_is_hidden_unless_enabled(client):
    assert client.post("/api/reset-db", headers={"X-Admin-Secret": "x"}).status_code == 404
    assert client.get("/api/reset-db?secret=x").status_code == 405  # 舊的 GET ?secret= 已失效


def test_reset_db_requires_secret_in_header(client, monkeypatch, db):
    monkeypatch.setattr(Main, "ALLOW_DB_RESET", True)
    monkeypatch.setattr(Main, "ADMIN_SECRET", "correct-secret")
    assert client.post("/api/reset-db").status_code == 403
    assert client.post("/api/reset-db", headers={"X-Admin-Secret": "wrong"}).status_code == 403
    assert client.post("/api/reset-db?secret=correct-secret").status_code == 403
    assert client.post("/api/reset-db", headers={"X-Admin-Secret": "correct-secret"}).status_code == 200


def test_reset_db_refuses_when_admin_secret_is_unset(client, monkeypatch):
    monkeypatch.setattr(Main, "ALLOW_DB_RESET", True)
    monkeypatch.setattr(Main, "ADMIN_SECRET", "")
    assert client.post("/api/reset-db", headers={"X-Admin-Secret": ""}).status_code == 403


# ---------- 錯誤訊息不外洩 ----------
def test_interview_ai_errors_are_logged_not_returned(client, login, fake_ai, caplog):
    login("u1")
    sid = client.post("/api/interview/start", json=START).json()["session_id"]
    fake_ai.replies.append(RuntimeError(SECRET))
    r = client.post("/api/interview/chat", json={"session_id": sid, "message": "hi"})
    assert r.status_code == 500 and SECRET not in r.text
    assert SECRET in caplog.text  # 詳細原因要留在伺服器 log 方便除錯

    client.post("/api/interview/chat", json={"session_id": sid, "message": "回答"})
    fake_ai.replies.append(RuntimeError(SECRET))
    r = client.post("/api/interview/finish", json={"session_id": sid})
    assert r.status_code == 500 and SECRET not in r.text


def test_heygen_upstream_error_body_is_not_returned(client, login, monkeypatch):
    login("u1")
    monkeypatch.setenv("LIVEAVATAR_API_KEY", "k")
    monkeypatch.setenv("LIVEAVATAR_AVATAR_ID", "a")

    class Upstream:
        status_code = 401
        text = f'{{"error": "invalid api key {SECRET}"}}'

    monkeypatch.setattr(heygen.requests, "post", lambda *args, **kwargs: Upstream())
    r = client.post("/heygen/embed")
    assert r.status_code == 502 and SECRET not in r.text


# ---------- CORS ----------
def preflight(client, origin):
    return client.options("/api/interview/start", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    })


@pytest.mark.parametrize("origin", [
    "https://cguimgraduatepj.me",
    "https://www.cguimgraduatepj.me",
    "https://ai-career-coach-gray-iota.vercel.app",
    "https://ai-career-coach-git-avatar-huang-merge-someone-projects.vercel.app",
    "http://localhost:3000",
])
def test_cors_allows_project_origins(client, origin):
    r = preflight(client, origin)
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] == origin
    assert "access-control-allow-credentials" not in r.headers


@pytest.mark.parametrize("origin", [
    "https://evil.vercel.app",
    "https://some-other-project.vercel.app",
    "http://ai-career-coach-gray-iota.vercel.app",
    "https://ai-career-coach-x.vercel.app.evil.com",
    "https://evil.com",
])
def test_cors_blocks_other_origins(client, origin):
    r = preflight(client, origin)
    assert "access-control-allow-origin" not in r.headers
