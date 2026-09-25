# auth.py — 共用的 Supabase JWT 驗證與 DB session 依賴
# 抽出成獨立模組，讓 Main.py 與各功能路由(interview.py、
# avatar.py、heygen.py)都能匯入 get_current_user，避免 Main.py 互相匯入造成循環匯入。

import os

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Header
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import Model
from Database import SessionLocal

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")

# Supabase 目前用非對稱金鑰（ES256）簽發 JWT，改用 JWKS 端點動態抓公鑰驗證，
# 不需要再保管共享密鑰；PyJWKClient 內建快取，不會每次請求都重打一次端點
_jwks_client: PyJWKClient | None = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        if not SUPABASE_URL:
            raise HTTPException(status_code=500, detail="伺服器未設定 SUPABASE_URL")
        _jwks_client = PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json")
    return _jwks_client


def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> Model.User:
    """驗證 Supabase 簽發的 JWT（Authorization: Bearer <token>），
    並取得（或建立）對應的本地使用者資料列。取代舊版直接信任前端傳入 user_id 的作法。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少身份驗證憑證")

    token = authorization.removeprefix("Bearer ").strip()

    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
        )
    except HTTPException:
        raise
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="憑證無效或已過期")
    except Exception as e:
        print(f"JWKS 驗證發生非預期錯誤: {e}")
        raise HTTPException(status_code=500, detail="無法驗證身份憑證，請稍後再試")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="憑證缺少使用者資訊")

    return _get_or_create_user(db, user_id, payload.get("email"))


def _release_email(db: Session, email: str, owner_id: str) -> None:
    """Supabase 保證同一時間一個 email 只屬於一個帳號，所以本地若有「其他 id」還佔著這個 email，
    代表那是已在 Supabase 刪除(或改過 email)的舊帳號。把它的 email 清空讓出來，
    否則 users.email 的 unique 限制會讓新帳號寫入失敗(同 email 重新註冊後整個網站 500)。
    舊帳號的履歷與面試紀錄保留但不轉給新帳號，避免 email 被重新註冊的人看到前一個人的資料。"""
    db.query(Model.User).filter(
        Model.User.email == email,
        Model.User.id != owner_id,
    ).update({"email": None}, synchronize_session=False)


def _get_or_create_user(db: Session, user_id: str, email: str | None) -> Model.User:
    user = db.query(Model.User).filter(Model.User.id == user_id).first()
    if user:
        # 使用者在 Supabase 改過 email 時，同步更新本地這份副本
        if email and user.email != email:
            _release_email(db, email, user_id)
            user.email = email
            db.commit()
        return user

    # 使用者是在 Supabase 端完成註冊，本地資料庫尚無對應資料列時，
    # 在第一次呼叫受保護 API 時建立履歷資料列（get-or-create）
    if email:
        _release_email(db, email, user_id)
    db.add(Model.User(id=user_id, email=email))
    try:
        db.commit()
    except IntegrityError:
        # 同一位新使用者的多個請求同時第一次打進來(例如進入頁面時同時呼叫多支 API)，
        # 其他請求已經先建好這筆資料，這裡改成直接讀取
        db.rollback()
    user = db.query(Model.User).filter(Model.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=500, detail="無法建立使用者資料，請稍後再試")
    return user
