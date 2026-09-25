# tests/conftest.py — pytest 共用設定
#
# 所有測試都在本機離線執行：
#   - 資料庫：每次測試執行建立一個暫存 SQLite 檔，每個測試前清空重建資料表
#   - AI / Supabase / Azure / HeyGen：一律換成假的，不會消耗任何 API 額度
#   - 不讀取本機 .env(避免測試結果受個人設定影響，換電腦或接 CI 也能跑)
#
# 環境變數必須在 import Main 之前設好，因為 Database.py、auth.py 等模組在 import 時就會讀取。

import os
import sys
import tempfile
from pathlib import Path

import dotenv

_TMP_DIR = tempfile.mkdtemp(prefix="ai_career_coach_tests_")
os.environ.update({
    "DATABASE_URL": f"sqlite:///{Path(_TMP_DIR, 'test.db').as_posix()}",
    "GEMINI_API_KEY": "test-dummy-key",
    "SUPABASE_URL": "https://test-project.supabase.co",
    "USE_GEMINI_CHAT": "0",
    "ALLOWED_ORIGINS": "https://cguimgraduatepj.me,https://www.cguimgraduatepj.me,http://localhost:3000",
    "ADMIN_SECRET": "",
    "ALLOW_DB_RESET": "0",
})
for name in ("ALLOWED_ORIGIN_REGEX", "GEMINI_MODEL", "MAX_RESUME_UPLOAD_MB"):
    os.environ.pop(name, None)
# Main.py 一開頭會呼叫 load_dotenv()；換成空函式，確保不會讀到本機 .env
dotenv.load_dotenv = lambda *args, **kwargs: False

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi import Depends  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import Main  # noqa: E402
import Model  # noqa: E402
import auth  # noqa: E402
import interview  # noqa: E402
import rate_limit  # noqa: E402
from Database import SessionLocal, engine  # noqa: E402


@pytest.fixture(autouse=True)
def clean_state():
    """每個測試前：清空資料表、限流計數、依賴覆寫。"""
    Model.Base.metadata.drop_all(bind=engine)
    Model.Base.metadata.create_all(bind=engine)
    rate_limit.reset_rate_limits()
    Main.app.dependency_overrides.clear()
    yield
    Main.app.dependency_overrides.clear()


@pytest.fixture
def client():
    # raise_server_exceptions=False：未處理的例外會像正式環境一樣變成 500 回應，而不是讓測試直接炸掉
    return TestClient(Main.app, raise_server_exceptions=False)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def login():
    """模擬已登入的使用者(跳過 Supabase JWT 驗證)。用法：login("u1")，可再次呼叫切換使用者。"""
    current = {}

    def _login(user_id="u1", email=None, **profile):
        session = SessionLocal()
        user = session.get(Model.User, user_id) or Model.User(id=user_id)
        user.email = email or f"{user_id}@example.com"
        for key, value in profile.items():
            setattr(user, key, value)
        session.merge(user)
        session.commit()
        session.close()
        current["id"] = user_id

        # 與正式的 get_current_user 一樣從 get_db 取得使用者(同一個請求共用同一個 DB session)
        def fake_current_user(db=Depends(auth.get_db)):
            return db.get(Model.User, current["id"])

        Main.app.dependency_overrides[auth.get_current_user] = fake_current_user
        return user_id

    return _login


class FakeAI:
    """取代 interview.generate_ai_text：依序回傳預先排好的回覆，並記錄每次呼叫的參數。"""

    def __init__(self):
        self.replies = []
        self.default = "好的，請繼續。"
        self.calls = []

    def __call__(self, prompt, system=None, json_mode=False):
        self.calls.append({"prompt": prompt, "system": system, "json_mode": json_mode})
        if self.replies:
            reply = self.replies.pop(0)
            if isinstance(reply, Exception):
                raise reply
            return reply
        return self.default


@pytest.fixture
def fake_ai(monkeypatch):
    ai = FakeAI()
    monkeypatch.setattr(interview, "generate_ai_text", ai)
    return ai


class FakeGemini:
    """取代 Main.gemini_client(履歷解析 / 履歷健檢用)。reply 可以是字串或例外。"""

    def __init__(self):
        self.reply = "{}"
        self.calls = []
        self.models = self

    def generate_content(self, model=None, contents=None, config=None):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if isinstance(self.reply, Exception):
            raise self.reply
        return type("Response", (), {"text": self.reply})()


@pytest.fixture
def fake_gemini(monkeypatch):
    gemini = FakeGemini()
    monkeypatch.setattr(Main, "gemini_client", gemini)
    return gemini


VALID_REPORT_JSON = (
    '{"overall_score": 72, "dimensions": {'
    '"technical": {"score": 7, "comment": "觀念正確"}, '
    '"communication": {"score": 8, "comment": "表達清楚"}, '
    '"problem_solving": {"score": 6, "comment": "追問時略顯猶豫"}}, '
    '"strengths": ["基礎扎實"], "improvements": ["多舉實例"], "summary": "整體表現不錯"}'
)
