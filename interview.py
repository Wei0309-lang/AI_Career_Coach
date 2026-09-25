# interview.py — 面試場次系統(模式選擇 + 場次對話 + AI 報告 + 歷史紀錄)
# 放在 repo 根目錄。Main.py 只需加:
#   from interview import router as interview_router
#   app.include_router(interview_router)
#
# 設計:每次面試是一個 InterviewSession(職位/難度/狀態/報告),
# 對話記憶限定在場次內。預設走本地 Ollama 模型(方便之後替換成自行訓練的版本),
# 雲端環境(如 Render,沒有安裝 Ollama)可設 USE_GEMINI_CHAT=1 切回 Gemini。
# 原本的 /chat 端點完全不受影響。

import json
import os
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy.orm import Session
from google import genai
from google.genai import types
from ollama import Client as OllamaClient

import Model
from auth import get_db, get_current_user
from resume_utils import flatten_resume_value

router = APIRouter(prefix="/api/interview", tags=["interview"])

gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "my-career-coach")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

VALID_POSITIONS = ["前端工程師", "後端工程師", "資安工程師", "全端工程師"]
VALID_LEVELS = ["實習生", "新鮮人", "資深工程師"]

# 資料庫存的是 UTC(naive datetime),回傳給前端顯示前轉成台灣時間(UTC+8,台灣沒有日光節約)
DISPLAY_TZ = timezone(timedelta(hours=8))


def format_local_time(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.replace(tzinfo=timezone.utc).astimezone(DISPLAY_TZ).strftime("%Y-%m-%d %H:%M")


def generate_ai_text(prompt: str, system: str | None = None, json_mode: bool = False) -> str:
    """依 USE_GEMINI_CHAT 決定用 Gemini 還是本地 Ollama 模型產生文字。
    預設(USE_GEMINI_CHAT 未設定或非 "1")走 Ollama,之後要換成自己訓練的模型，
    改 OLLAMA_MODEL 指到新的 Modelfile 名稱即可，不需要再改這支程式。

    system:明確指定 system prompt。對 Ollama 來說會取代 Modelfile 裡的 SYSTEM(面試官人設),
            產生報告這類「不是扮演面試官」的任務要帶,避免模型繼續用面試官身分回話。
    json_mode:要求模型只輸出合法 JSON(Ollama format="json"、Gemini application/json)。
            本地 Llama 3 不開這個選項時,常常漏掉最後一個 "}" 導致報告解析失敗。"""
    if os.getenv("USE_GEMINI_CHAT", "0") == "1":
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json" if json_mode else None,
        )
        g = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt, config=config)
        return (g.text or "").strip()

    messages = [{"role": "user", "content": prompt}]
    if system:
        messages.insert(0, {"role": "system", "content": system})

    client = OllamaClient(host=OLLAMA_HOST)
    response = client.chat(
        model=OLLAMA_MODEL,
        messages=messages,
        format="json" if json_mode else None,
        options={"temperature": 0.3, "num_predict": 1024, "top_k": 40, "top_p": 0.9},
    )
    if "message" in response and "content" in response["message"]:
        return (response["message"]["content"] or "").strip()
    return ""


def build_system_prompt(user, position: str, level: str) -> str:
    profile = f"""
    【求職者基本資訊】：
    - 姓名：{user.full_name or '未填寫'}
    - 個人簡介：{user.summary or '未填寫'}
    - 專業技能：{user.skills or '未填寫'}
    - 工作經歷：{user.experience or '未填寫'}
    """
    return f"""
    【最高指導原則】：你必須、絕對只能使用「繁體中文 (Traditional Chinese)」回答。

    你是「林經理」,一位嚴格且資深的科技業技術面試官。
    本場面試的目標職位是「{position}」,應徵者級別為「{level}」。
    請根據該職位的核心技能與該級別的合理期望來設計問題與評估標準:
    - 實習生:重基礎觀念與學習潛力,語氣可稍微引導
    - 新鮮人:重基礎扎實度、專案經驗與實作細節
    - 資深工程師:重系統設計、技術決策、深度追問底層原理
    {profile}
    行為準則:
    1. 語氣專業、冷靜,保持適當距離。
    2. 一次只問一個問題,每次發言不超過三句話。
    3. 根據回答追問底層原理,不接受表面答案。
    4. 求職者卡住時只給提示,絕不給完整答案;觀念錯誤要直接指出。
    5. 不要使用任何條列符號、表情符號,像真人口語一樣說話。
    """


# ---------- 開始面試 ----------
class StartRequest(BaseModel):
    position: str
    level: str


@router.post("/start")
def start_interview(
    req: StartRequest,
    user: Model.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if req.position not in VALID_POSITIONS or req.level not in VALID_LEVELS:
        raise HTTPException(status_code=400, detail="無效的職位或級別")

    session = Model.InterviewSession(
        user_id=user.id, position=req.position, level=req.level
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # 產生面試官開場白(自我介紹 + 第一個問題)
    prompt = build_system_prompt(user, req.position, req.level) + """
    現在面試正式開始。請說出你的開場白:先用一句話自我介紹,
    然後請應徵者自我介紹。總共不超過三句話,只輸出你要說的話。
    """
    try:
        opening = generate_ai_text(prompt) or "您好,我是林經理,今天由我負責您的技術面試。請先簡單自我介紹。"
    except Exception:
        opening = "您好,我是林經理,今天由我負責您的技術面試。請先簡單自我介紹。"

    db.add(Model.ChatMessage(
        user_id=user.id, role="assistant", content=opening,
        session_id=session.id,
    ))
    db.commit()

    return {"session_id": session.id, "opening": opening}


# ---------- 場次內對話 ----------
class InterviewChatRequest(BaseModel):
    session_id: str
    message: str


@router.post("/chat")
def interview_chat(
    req: InterviewChatRequest,
    user: Model.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(Model.InterviewSession).filter(
        Model.InterviewSession.id == req.session_id
    ).first()
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="面試場次不存在")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="此面試已結束")

    # 場次內「最近」20 則對話(控制 token):先倒序取 20 則再反轉回時間順序。
    # 若直接正序 limit(20) 會拿到最舊的 20 則,面試超過 10 輪後面試官就看不到最近的回答
    history = db.query(Model.ChatMessage).filter(
        Model.ChatMessage.session_id == req.session_id
    ).order_by(Model.ChatMessage.created_at.desc()).limit(20).all()[::-1]

    convo = "\n".join(
        ("面試者:" if m.role == "user" else "面試官:") + m.content for m in history
    )

    db.add(Model.ChatMessage(
        user_id=user.id, role="user", content=req.message,
        session_id=req.session_id,
    ))

    prompt = (
        build_system_prompt(user, session.position, session.level)
        + "\n以下是目前的面試對話:\n" + convo
        + "\n面試者:" + req.message
        + "\n\n請以面試官身分回覆,只輸出面試官要說的話:"
    )
    try:
        ai_response = generate_ai_text(prompt) or "(面試官正看著你,等待更具體的回答...)"
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"AI 服務連線失敗: {e}")

    db.add(Model.ChatMessage(
        user_id=user.id, role="assistant", content=ai_response,
        session_id=req.session_id,
    ))
    db.commit()
    return {"response": ai_response}


# ---------- 結束面試 → 生成報告 ----------
class FinishRequest(BaseModel):
    session_id: str


REPORT_SCHEMA_HINT = """{
  "overall_score": 0到100的整數,
  "dimensions": {
    "technical": {"score": 0到10, "comment": "一句話評語"},
    "communication": {"score": 0到10, "comment": "一句話評語"},
    "problem_solving": {"score": 0到10, "comment": "一句話評語"}
  },
  "strengths": ["優點一", "優點二"],
  "improvements": ["改進建議一", "改進建議二"],
  "summary": "三句話以內的總評"
}"""

REPORT_SYSTEM_PROMPT = "你是一位專業的技術面試評估顧問，只輸出 JSON，不輸出任何其他文字。"
# 模型偶爾仍會輸出不合格式的內容，重試一次通常就會成功，不必讓使用者自己再按一次
REPORT_MAX_ATTEMPTS = 2


def _to_score(value, upper: int) -> int:
    """把模型給的分數(8、"8"、8.5、"8/10" 等)轉成 0~upper 的整數;解析不出數字就給 0。"""
    match = re.search(r"\d+(?:\.\d+)?", str(value)) if value is not None else None
    if not match:
        return 0
    return max(0, min(upper, round(float(match.group()))))


def _to_text_list(value) -> list[str]:
    if value is None:
        return []
    items = value if isinstance(value, list) else [value]
    return [text for text in (flatten_resume_value(item) for item in items) if text]


# 前端直接讀 report.dimensions.technical.score 等欄位，缺任何一層就會整頁崩潰，
# 因此報告一律先經過這組 schema 補齊預設值、校正型別與分數範圍，再存檔或回傳
class DimensionScore(BaseModel):
    score: int = 0
    comment: str = ""

    @field_validator("score", mode="before")
    @classmethod
    def _coerce_score(cls, v):
        return _to_score(v, 10)

    @field_validator("comment", mode="before")
    @classmethod
    def _coerce_comment(cls, v):
        return flatten_resume_value(v)


class ReportDimensions(BaseModel):
    technical: DimensionScore = Field(default_factory=DimensionScore)
    communication: DimensionScore = Field(default_factory=DimensionScore)
    problem_solving: DimensionScore = Field(default_factory=DimensionScore)

    @field_validator("technical", "communication", "problem_solving", mode="before")
    @classmethod
    def _coerce_dimension(cls, v):
        return v if isinstance(v, dict) else {}


class InterviewReport(BaseModel):
    overall_score: int = 0
    dimensions: ReportDimensions = Field(default_factory=ReportDimensions)
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    summary: str = ""

    @field_validator("overall_score", mode="before")
    @classmethod
    def _coerce_overall(cls, v):
        return _to_score(v, 100)

    @field_validator("dimensions", mode="before")
    @classmethod
    def _coerce_dimensions(cls, v):
        return v if isinstance(v, dict) else {}

    @field_validator("strengths", "improvements", mode="before")
    @classmethod
    def _coerce_list(cls, v):
        return _to_text_list(v)

    @field_validator("summary", mode="before")
    @classmethod
    def _coerce_summary(cls, v):
        return flatten_resume_value(v)


def parse_report(raw: str) -> InterviewReport | None:
    """從模型輸出中取出報告 JSON;格式不對或根本不像報告時回傳 None。"""
    text = (raw or "").replace("```json", "").replace("```", "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    # 連總分和各維度都沒有的 JSON(例如 {} 或模型自創的格式)不算報告，避免存下一份全 0 分的假報告
    if not isinstance(data, dict) or not {"overall_score", "dimensions"} & data.keys():
        return None
    try:
        return InterviewReport.model_validate(data)
    except ValidationError:
        return None


def load_report(report_json: str | None) -> dict | None:
    """讀取已存檔的報告並補齊欄位，讓修正前存下的舊報告也不會讓前端崩潰。"""
    if not report_json:
        return None
    try:
        return InterviewReport.model_validate(json.loads(report_json)).model_dump()
    except (json.JSONDecodeError, ValidationError):
        return None


@router.post("/finish")
def finish_interview(
    req: FinishRequest,
    user: Model.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(Model.InterviewSession).filter(
        Model.InterviewSession.id == req.session_id
    ).first()
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="面試場次不存在")

    history = db.query(Model.ChatMessage).filter(
        Model.ChatMessage.session_id == req.session_id
    ).order_by(Model.ChatMessage.created_at.asc()).all()

    if len(history) < 3:
        raise HTTPException(status_code=400, detail="對話太短,無法產生有意義的報告,請多回答幾題再結束")

    transcript = "\n".join(
        ("面試者:" if m.role == "user" else "面試官:") + m.content for m in history
    )

    prompt = f"""你是一位專業的技術面試評估顧問。以下是一場「{session.position}({session.level})」模擬面試的完整逐字稿。
請客觀評估面試者的表現,並「只輸出」符合以下格式的 JSON,不要有任何其他文字、不要用 markdown 程式碼區塊:

{REPORT_SCHEMA_HINT}

評估重點:回答的技術正確性與深度(technical)、表達清晰度(communication)、面對追問與不會的問題時的應對(problem_solving)。
評語與建議必須具體、可執行,使用繁體中文。

=== 面試逐字稿 ===
{transcript}
"""
    report = None
    for attempt in range(1, REPORT_MAX_ATTEMPTS + 1):
        try:
            raw = generate_ai_text(prompt, system=REPORT_SYSTEM_PROMPT, json_mode=True)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI 服務連線失敗: {e}")
        report = parse_report(raw)
        if report:
            break
        print(f"報告格式解析失敗(第 {attempt} 次),模型原始輸出: {raw[:300]}")

    if report is None:
        raise HTTPException(status_code=502, detail="報告格式解析失敗,請再試一次")

    report_data = report.model_dump()
    session.status = "finished"
    session.finished_at = datetime.utcnow()
    session.report_json = json.dumps(report_data, ensure_ascii=False)
    db.commit()

    return {"report": report_data}


# ---------- 歷史紀錄 ----------
@router.get("/history")
def interview_history(
    user: Model.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = db.query(Model.InterviewSession).filter(
        Model.InterviewSession.user_id == user.id,
        Model.InterviewSession.status == "finished",
    ).order_by(Model.InterviewSession.created_at.desc()).all()

    result = []
    for s in sessions:
        report = load_report(s.report_json) or {}
        result.append({
            "session_id": s.id,
            "position": s.position,
            "level": s.level,
            "date": format_local_time(s.created_at),
            "overall_score": report.get("overall_score"),
            "summary": report.get("summary", ""),
        })
    return {"sessions": result}

# ---------- 單場詳細報告與逐字稿 ----------
@router.get("/detail/{session_id}")
def interview_detail(
    session_id: str,
    user: Model.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(Model.InterviewSession).filter(
        Model.InterviewSession.id == session_id
    ).first()
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="面試場次不存在")

    messages = db.query(Model.ChatMessage).filter(
        Model.ChatMessage.session_id == session_id
    ).order_by(Model.ChatMessage.created_at.asc()).all()

    return {
        "position": session.position,
        "level": session.level,
        "date": format_local_time(session.created_at),
        "report": load_report(session.report_json),
        "transcript": [
            {"role": m.role, "content": m.content} for m in messages
        ],
    }
