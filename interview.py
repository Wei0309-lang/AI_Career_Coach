# interview.py — 面試場次系統(模式選擇 + 場次對話 + AI 報告 + 歷史紀錄)
# 放在 repo 根目錄。Main.py 只需加:
#   from interview import router as interview_router
#   app.include_router(interview_router)
#
# 設計:每次面試是一個 InterviewSession(職位/難度/狀態/報告),
# 對話記憶限定在場次內。全部走 Gemini(本地與雲端皆可用),
# 原本的 /chat 端點完全不受影響。

import json
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from google import genai

import Model
from Database import SessionLocal

router = APIRouter(prefix="/api/interview", tags=["interview"])

gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

VALID_POSITIONS = ["前端工程師", "後端工程師", "資安工程師", "全端工程師"]
VALID_LEVELS = ["實習生", "新鮮人", "資深工程師"]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
    user_id: str
    position: str
    level: str


@router.post("/start")
def start_interview(req: StartRequest, db: Session = Depends(get_db)):
    if req.position not in VALID_POSITIONS or req.level not in VALID_LEVELS:
        raise HTTPException(status_code=400, detail="無效的職位或級別")

    user = db.query(Model.User).filter(Model.User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")

    session = Model.InterviewSession(
        user_id=req.user_id, position=req.position, level=req.level
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
        g = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        opening = (g.text or "").strip() or "您好,我是林經理,今天由我負責您的技術面試。請先簡單自我介紹。"
    except Exception:
        opening = "您好,我是林經理,今天由我負責您的技術面試。請先簡單自我介紹。"

    db.add(Model.ChatMessage(
        user_id=req.user_id, role="assistant", content=opening,
        session_id=session.id,
    ))
    db.commit()

    return {"session_id": session.id, "opening": opening}


# ---------- 場次內對話 ----------
class InterviewChatRequest(BaseModel):
    session_id: str
    user_id: str
    message: str


@router.post("/chat")
def interview_chat(req: InterviewChatRequest, db: Session = Depends(get_db)):
    session = db.query(Model.InterviewSession).filter(
        Model.InterviewSession.id == req.session_id
    ).first()
    if not session or session.user_id != req.user_id:
        raise HTTPException(status_code=404, detail="面試場次不存在")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="此面試已結束")

    user = db.query(Model.User).filter(Model.User.id == req.user_id).first()

    # 場次內的歷史對話(最多取近 20 則,控制 token)
    history = db.query(Model.ChatMessage).filter(
        Model.ChatMessage.session_id == req.session_id
    ).order_by(Model.ChatMessage.created_at.asc()).limit(20).all()

    convo = "\n".join(
        ("面試者:" if m.role == "user" else "面試官:") + m.content for m in history
    )

    db.add(Model.ChatMessage(
        user_id=req.user_id, role="user", content=req.message,
        session_id=req.session_id,
    ))

    prompt = (
        build_system_prompt(user, session.position, session.level)
        + "\n以下是目前的面試對話:\n" + convo
        + "\n面試者:" + req.message
        + "\n\n請以面試官身分回覆,只輸出面試官要說的話:"
    )
    try:
        g = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        ai_response = (g.text or "").strip() or "(面試官正看著你,等待更具體的回答...)"
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"AI 服務連線失敗: {e}")

    db.add(Model.ChatMessage(
        user_id=req.user_id, role="assistant", content=ai_response,
        session_id=req.session_id,
    ))
    db.commit()
    return {"response": ai_response}


# ---------- 結束面試 → 生成報告 ----------
class FinishRequest(BaseModel):
    session_id: str
    user_id: str


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


@router.post("/finish")
def finish_interview(req: FinishRequest, db: Session = Depends(get_db)):
    session = db.query(Model.InterviewSession).filter(
        Model.InterviewSession.id == req.session_id
    ).first()
    if not session or session.user_id != req.user_id:
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
    try:
        g = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        raw = (g.text or "").strip()
        # 移除可能出現的 markdown 圍欄
        raw = raw.replace("```json", "").replace("```", "").strip()
        report = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="報告格式解析失敗,請再試一次")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 服務連線失敗: {e}")

    session.status = "finished"
    session.finished_at = datetime.utcnow()
    session.report_json = json.dumps(report, ensure_ascii=False)
    db.commit()

    return {"report": report}


# ---------- 歷史紀錄 ----------
@router.get("/history/{user_id}")
def interview_history(user_id: str, db: Session = Depends(get_db)):
    sessions = db.query(Model.InterviewSession).filter(
        Model.InterviewSession.user_id == user_id,
        Model.InterviewSession.status == "finished",
    ).order_by(Model.InterviewSession.created_at.desc()).all()

    result = []
    for s in sessions:
        report = json.loads(s.report_json) if s.report_json else {}
        result.append({
            "session_id": s.id,
            "position": s.position,
            "level": s.level,
            "date": s.created_at.strftime("%Y-%m-%d %H:%M"),
            "overall_score": report.get("overall_score"),
            "summary": report.get("summary", ""),
        })
    return {"sessions": result}

# ---------- 單場詳細報告與逐字稿 ----------
@router.get("/detail/{session_id}")
def interview_detail(session_id: str, user_id: str, db: Session = Depends(get_db)):
    session = db.query(Model.InterviewSession).filter(
        Model.InterviewSession.id == session_id
    ).first()
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="面試場次不存在")

    messages = db.query(Model.ChatMessage).filter(
        Model.ChatMessage.session_id == session_id
    ).order_by(Model.ChatMessage.created_at.asc()).all()

    return {
        "position": session.position,
        "level": session.level,
        "date": session.created_at.strftime("%Y-%m-%d %H:%M"),
        "report": json.loads(session.report_json) if session.report_json else None,
        "transcript": [
            {"role": m.role, "content": m.content} for m in messages
        ],
    }
