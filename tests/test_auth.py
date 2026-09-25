# Supabase JWT 驗證與本地使用者資料(get-or-create)
import threading

import pytest

import Model
import auth

H = {"Authorization": "Bearer fake-token"}


@pytest.fixture
def supabase_token(monkeypatch):
    """跳過真正的 JWKS 簽章驗證，直接指定 JWT 解出來的內容(sub = Supabase 使用者 id)。"""
    payload = {}

    class FakeJwks:
        def get_signing_key_from_jwt(self, token):
            return type("Key", (), {"key": "k"})()

    monkeypatch.setattr(auth, "_get_jwks_client", lambda: FakeJwks())
    monkeypatch.setattr(auth.jwt, "decode", lambda *args, **kwargs: dict(payload))

    def as_user(sub, email):
        payload.clear()
        payload.update(sub=sub, email=email)

    return as_user


def test_missing_token_is_401(client):
    assert client.get("/api/resume").status_code == 401


def test_invalid_token_is_401(client, monkeypatch):
    class RejectingJwks:
        def get_signing_key_from_jwt(self, token):
            raise auth.jwt.PyJWTError("bad signature")

    monkeypatch.setattr(auth, "_get_jwks_client", lambda: RejectingJwks())
    r = client.get("/api/resume", headers=H)
    assert r.status_code == 401 and r.json()["detail"] == "憑證無效或已過期"


def test_missing_supabase_url_gives_clear_500(client, monkeypatch):
    """正式環境曾因 Render 沒設 SUPABASE_URL，所有需要登入的 API 都回 500。"""
    monkeypatch.setattr(auth, "SUPABASE_URL", "")
    monkeypatch.setattr(auth, "_jwks_client", None)
    r = client.get("/api/resume", headers=H)
    assert r.status_code == 500 and "SUPABASE_URL" in r.json()["detail"]


def test_first_request_creates_local_user(client, supabase_token, db):
    supabase_token("uuid-1", "a@example.com")
    assert client.get("/api/resume", headers=H).status_code == 200
    assert db.get(Model.User, "uuid-1").email == "a@example.com"


def test_reregistered_email_gets_fresh_account_without_old_data(client, supabase_token, db, fake_gemini):
    """在 Supabase 刪除帳號後用同一個 email 重新註冊(新的 sub)。修正前 email unique 衝突 → 整個網站 500。"""
    supabase_token("old-uuid", "reuse@example.com")
    client.post("/api/resume", headers=H, json={"fullName": "舊使用者", "summary": "s", "skills": "k", "experience": "e"})

    supabase_token("new-uuid", "reuse@example.com")
    r = client.get("/api/resume", headers=H)
    assert r.status_code == 200
    assert r.json()["fullName"] == ""  # 新帳號看不到前一個人的履歷
    db.expire_all()
    assert db.get(Model.User, "new-uuid").email == "reuse@example.com"
    old = db.get(Model.User, "old-uuid")
    assert old.email is None and old.full_name == "舊使用者"  # 舊資料保留，只讓出 email


def test_email_change_in_supabase_is_synced(client, supabase_token, db):
    supabase_token("uuid-1", "before@example.com")
    client.get("/api/resume", headers=H)
    supabase_token("uuid-1", "after@example.com")
    assert client.get("/api/resume", headers=H).status_code == 200
    db.expire_all()
    assert db.get(Model.User, "uuid-1").email == "after@example.com"


def test_concurrent_first_requests_of_new_user_all_succeed(client, supabase_token, db):
    """新使用者第一次進頁面時多支 API 同時打進來，修正前會有部分請求因重複 INSERT 回 500。"""
    supabase_token("race-uuid", "race@example.com")
    codes = []

    def hit():
        codes.append(client.get("/api/resume", headers=H).status_code)

    threads = [threading.Thread(target=hit) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert codes == [200] * 8
    assert db.query(Model.User).filter_by(email="race@example.com").count() == 1
