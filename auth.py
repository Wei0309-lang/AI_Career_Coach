# auth.py — 共用的 Supabase JWT 驗證與 DB session 依賴
# 抽出成獨立模組，讓 Main.py 與各功能路由(interview.py、resume_upload.py、
# avatar.py、heygen.py)都能匯入 get_current_user，避免 Main.py 互相匯入造成循環匯入。

import os

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Header
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

    user = db.query(Model.User).filter(Model.User.id == user_id).first()
    if not user:
        # 使用者是在 Supabase 端完成註冊，本地資料庫尚無對應資料列時，
        # 在第一次呼叫受保護 API 時建立履歷資料列（get-or-create）
        user = Model.User(id=user_id, email=payload.get("email"))
        db.add(user)
        db.commit()
        db.refresh(user)

    return user
