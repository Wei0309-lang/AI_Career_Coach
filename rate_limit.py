# rate_limit.py — 依「登入使用者」限制呼叫頻率，防止有人註冊帳號後狂打 AI / 語音 / HeyGen 端點燒光額度
#
# 用法(放在需要保護的端點參數裡，取代原本的 Depends(get_current_user)):
#   user: Model.User = Depends(rate_limited("interview_chat"))
#
# 計數存在記憶體(滑動視窗)，只適用單一後端行程；Render 免費方案只有一個 instance，
# 重新部署或重啟後計數會歸零，對專題規模已足夠。之後若要開多個 instance 需改用 Redis 之類的共享儲存。

import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException

import Model
from auth import get_current_user

# 每個 bucket:(時間窗內最多幾次, 時間窗秒數)。數值以「正常使用不會碰到」為準
RATE_LIMITS: dict[str, tuple[int, int]] = {
    "interview_start": (10, 600),    # 開新面試:10 分鐘 10 場
    "interview_chat": (20, 60),      # 面試對話:每分鐘 20 則(真人打字/說話遠低於此)
    "interview_finish": (10, 600),   # 產生報告:10 分鐘 10 次
    "resume_parse": (10, 600),       # 履歷檔案解析
    "resume_submit": (10, 600),      # 儲存履歷 + AI 健檢建議
    "legacy_chat": (20, 60),         # 舊版 /chat
    "tts": (40, 60),                 # Azure 語音合成(每則面試官回覆一次)
    "heygen_embed": (5, 3600),       # HeyGen 付費額度，限制最嚴
}

_hits: dict[tuple[str, str], deque] = defaultdict(deque)
_lock = threading.Lock()


def check_rate_limit(bucket: str, user_id: str) -> None:
    limit, window = RATE_LIMITS[bucket]
    now = time.monotonic()
    with _lock:
        hits = _hits[(bucket, user_id)]
        while hits and now - hits[0] >= window:
            hits.popleft()
        if len(hits) >= limit:
            retry_after = int(window - (now - hits[0])) + 1
            raise HTTPException(
                status_code=429,
                detail=f"操作太頻繁，請約 {retry_after} 秒後再試",
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)


def rate_limited(bucket: str):
    """產生一個 FastAPI 依賴：先驗證登入身份，再檢查該使用者在此 bucket 的呼叫頻率。"""
    if bucket not in RATE_LIMITS:
        raise ValueError(f"未定義的 rate limit bucket: {bucket}")

    def dependency(user: Model.User = Depends(get_current_user)) -> Model.User:
        check_rate_limit(bucket, user.id)
        return user

    return dependency


def reset_rate_limits() -> None:
    """清空所有計數(測試用)。"""
    with _lock:
        _hits.clear()
