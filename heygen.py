# heygen.py — HeyGen LiveAvatar 整合 Router
# 放在 repo 根目錄(與 Main.py、avatar.py 同層)
# 職責:向 LiveAvatar API 建立 embed session,把 iframe 網址回傳給前端。
#       API key 只存在後端,絕不暴露到瀏覽器。
#
# 需要的環境變數(.env):
#   LIVEAVATAR_API_KEY      在 app.liveavatar.com 開發者頁面取得
#   LIVEAVATAR_AVATAR_ID    你在 dashboard 選定的 avatar 的 ID
#   LIVEAVATAR_CONTEXT_ID   你建立的面試官人設(Context/Knowledge Base)的 ID
#   LIVEAVATAR_SANDBOX      預設 1(沙盒模式,不扣 credits);正式 demo 才改 0

import os

import requests
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/heygen", tags=["heygen"])

LIVEAVATAR_API = "https://api.liveavatar.com/v2/embeddings"


@router.post("/embed")
def create_embed():
    """建立一個 LiveAvatar embed,回傳 iframe 用的網址。"""
    api_key = os.getenv("LIVEAVATAR_API_KEY")
    avatar_id = os.getenv("LIVEAVATAR_AVATAR_ID")
    context_id = os.getenv("LIVEAVATAR_CONTEXT_ID")
    is_sandbox = os.getenv("LIVEAVATAR_SANDBOX", "1") == "1"

    if not api_key or not avatar_id:
        raise HTTPException(
            status_code=500,
            detail="伺服器未設定 LIVEAVATAR_API_KEY / LIVEAVATAR_AVATAR_ID",
        )

    payload = {"avatar_id": avatar_id, "is_sandbox": is_sandbox}
    if context_id:
        payload["context_id"] = context_id
        voice_id = os.getenv("LIVEAVATAR_VOICE_ID")
    if voice_id:
        payload["voice_id"] = voice_id

    try:
        resp = requests.post(
            LIVEAVATAR_API,
            headers={
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"LiveAvatar 連線失敗: {e}")

    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"LiveAvatar API 錯誤 {resp.status_code}: {resp.text[:300]}",
        )

    data = resp.json().get("data", {})
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=502, detail="LiveAvatar 未回傳 embed 網址")

    return {"url": url, "sandbox": is_sandbox}
