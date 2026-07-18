from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Depends, HTTPException, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ollama import AsyncClient
from google import genai
from pypdf import PdfReader
from docx import Document
import jwt
from jwt import PyJWKClient
import Model
from Database import SessionLocal, engine
import os
import io
import json
from avatar import router as avatar_router
from heygen import router as heygen_router
from interview import router as interview_router
from resume_upload import router as resume_upload_router


# 自動建立資料表
Model.Base.metadata.create_all(bind=engine)

app = FastAPI()
gemini_client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

# --- 可移植性設定：從環境變數讀取，方便在不同環境部署 ---
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "my-career-coach")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]
MAX_RESUME_UPLOAD_MB = int(os.getenv("MAX_RESUME_UPLOAD_MB", "10"))

# Supabase 目前用非對稱金鑰（ES256）簽發 JWT，改用 JWKS 端點動態抓公鑰驗證，
# 不需要再保管共享密鑰；PyJWKClient 內建快取，不會每次請求都重打一次端點
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        if not SUPABASE_URL:
            raise HTTPException(status_code=500, detail="伺服器未設定 SUPABASE_URL")
        _jwks_client = PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json")
    return _jwks_client

# 升級 CORS 設定，用 regex 包容所有 Vercel 分支與預覽網址
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app", # 允許任何 vercel.app 結尾的來源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(avatar_router)
app.include_router(heygen_router)
app.include_router(interview_router)
app.include_router(resume_upload_router)

class ChatRequest(BaseModel):
    message: str

class ResumeData(BaseModel):
    fullName: str
    summary: str
    skills: str
    experience: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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


# 「重置資料庫」的 API (用來解決舊欄位衝突)
# 需在 query string 帶上 secret=<ADMIN_SECRET> 才能執行，防止公開網路任意呼叫
@app.get("/api/reset-db")
def reset_database(secret: str = ""):
    if not ADMIN_SECRET or secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="禁止存取：缺少或錯誤的 secret")
    try:
        # 這會強制刪除舊有的資料表，並依照最新的 Model.py 重新建立完整欄位
        Model.Base.metadata.drop_all(bind=engine)
        Model.Base.metadata.create_all(bind=engine)
        return {"message": "✅ 資料庫已成功重置更新！請回到前端重新註冊帳號。"}
    except Exception as e:
        return {"message": f"❌ 重置失敗: {str(e)}"}


@app.get("/")
def root():
    return {"message": "AI Career Coach API is running"}


# 讀取現有履歷資料的 API
@app.get("/api/resume")
def get_resume(user: Model.User = Depends(get_current_user)):
    # 將資料庫中的內容回傳給前端，若為 None 則給予空字串避免前端 input 報錯
    return {
        "fullName": user.full_name or "",
        "summary": user.summary or "",
        "skills": user.skills or "",
        "experience": user.experience or ""
    }

def _extract_text_from_pdf(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    if reader.is_encrypted:
        raise ValueError("PDF 檔案已加密，請上傳未加密的檔案")
    pages_text = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages_text).strip()


def _extract_text_from_docx(content: bytes) -> str:
    document = Document(io.BytesIO(content))
    return "\n".join(p.text for p in document.paragraphs).strip()


# --- 履歷檔案上傳解析 API（PDF / Word，解析完即丟棄檔案本體，不做任何儲存）---
@app.post("/api/resume/parse")
async def parse_resume_file(file: UploadFile = File(...), user: Model.User = Depends(get_current_user)):
    filename = (file.filename or "").lower()
    if filename.endswith(".pdf"):
        file_kind = "pdf"
    elif filename.endswith(".docx"):
        file_kind = "docx"
    else:
        raise HTTPException(status_code=400, detail="僅支援 PDF 或 Word(.docx) 檔案")

    content = await file.read()
    if len(content) > MAX_RESUME_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"檔案大小超過 {MAX_RESUME_UPLOAD_MB}MB 上限")

    try:
        if file_kind == "pdf":
            raw_text = _extract_text_from_pdf(content)
        else:
            raw_text = _extract_text_from_docx(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="檔案解析失敗，請確認檔案未毀損")

    if len(raw_text) < 20:
        raise HTTPException(
            status_code=400,
            detail="偵測不到可選取的文字內容，請確認上傳的是文字型 PDF/Word（不支援掃描圖檔）"
        )

    prompt = f"""你是一個履歷資料整理助手。請將以下履歷原文整理成 JSON 格式，欄位為：
fullName（姓名）、summary（個人簡介）、skills（專業技能）、experience（工作/專案經歷）。
若原文中找不到某欄位對應的資訊，該欄位請回傳空字串。
只回傳 JSON 本身，不要加上任何說明文字或 markdown 標記。

【履歷原文】
{raw_text}
"""

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        raw_json = response.text.strip()
        if raw_json.startswith("```"):
            raw_json = raw_json.strip("`")
            if raw_json.lower().startswith("json"):
                raw_json = raw_json.split("\n", 1)[1] if "\n" in raw_json else ""
        parsed = json.loads(raw_json)
    except Exception as e:
        print(f"履歷 AI 解析失敗: {e}")
        raise HTTPException(status_code=502, detail="AI 解析履歷內容失敗，請稍後再試")

    return {
        "fullName": parsed.get("fullName", "") or "",
        "summary": parsed.get("summary", "") or "",
        "skills": parsed.get("skills", "") or "",
        "experience": parsed.get("experience", "") or "",
    }


# --- 履歷整合 API ---
@app.post("/api/resume")
def submit_resume(data: ResumeData, user: Model.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 存入資料庫以供後續 AI 面試官參考
    user.full_name = data.fullName
    user.summary = data.summary
    user.skills = data.skills
    user.experience = data.experience
    db.commit()

    prompt = f"""你是一位專業的履歷顧問。請根據以下這份履歷,給出具體、可執行的改善建議。
請用繁體中文,條列 3-5 點重點,語氣專業但友善。
輸出純文字即可:不要使用任何 Markdown 符號(如 **、*、#、`),
條列請直接用「1. 2. 3.」與「・」,重點詞彙不需要加粗。

【個人簡介】
{data.summary}

【專業技能】
{data.skills}

【工作經歷】
{data.experience}

請針對內容的具體性、量化成就、技能呈現等面向給建議。"""

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        suggestion = response.text
    except Exception as e:
        print(f"AI 呼叫失敗: {e}")
        suggestion = f"AI 服務暫時無法使用，錯誤訊息: {e}"

    return {"suggestion": suggestion}


# --- AI 對話 API (嚴格面試官版 - 包含履歷內容與對話記憶) ---
@app.post("/chat")
async def chat_endpoint(request: ChatRequest, user: Model.User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_message = request.message
    model_name = OLLAMA_MODEL

    print(f"------------\n收到使用者問題 (ID: {user.id}): {user_message}")

    # 將使用者的履歷資訊動態塞入系統 prompt 中，形成個人化上下文
    profile_context = f"""
    【求職者基本資訊】：
    - 姓名：{user.full_name or '未填寫'}
    - 個人簡介：{user.summary or '未填寫'}
    - 專業技能：{user.skills or '未填寫'}
    - 工作經歷：{user.experience or '未填寫'}
    """

    system_prompt = f"""
    【最高指導原則】：你必須、絕對只能使用「繁體中文 (Traditional Chinese)」回答。嚴禁使用英文或其他語言作為主要溝通語言（技術專有名詞如 React, API, Python 除外）。如果你使用英文回答，系統將會崩潰。

    你現在是一位嚴格且資深的科技業技術面試官 (Senior Tech Interviewer)。你的目標是評估求職者的真實技術實力。
    {profile_context}

    請嚴格遵守以下行為準則：
    1. 【保持專業距離】：語氣要專業、冷靜，不要過度熱情。
    2. 【批判性思維】：不要輕易接受使用者的回答，請立刻追問底層原理。
    3. 【拒絕直接給答案】：當使用者卡住時，只能給提示，絕對不要直接寫出完整答案。
    4. 【糾正錯誤】：觀念有誤請直接指出錯誤點。
    """

    # 1️⃣ 從資料庫撈取最近 10 筆歷史訊息，建立持久對話記憶
    history_records = db.query(Model.ChatMessage)\
                        .filter(Model.ChatMessage.user_id == user.id)\
                        .order_by(Model.ChatMessage.created_at.asc())\
                        .limit(10).all()

    # 建立 Ollama 的訊息傳送矩陣
    messages_payload = [{"role": "system", "content": system_prompt}]

    # 把歷史紀錄塞進去
    for msg in history_records:
        messages_payload.append({"role": msg.role, "content": msg.content})

    # 把當前加料過的使用者問題放入末尾
    enforced_user_message = f"{user_message}\n\n(系統提示：請務必只使用繁體中文扮演面試官回覆)"
    messages_payload.append({"role": "user", "content": enforced_user_message})

    # 將當前使用者的提問寫入資料庫
    new_user_msg = Model.ChatMessage(user_id=user.id, role="user", content=user_message)
    db.add(new_user_msg)

    try:
        # 🆕 ============================================================
        # 本地開發模式：.env 設 USE_GEMINI_CHAT=1 時改用 Gemini 回覆，
        # 不需要安裝 Ollama。Render 雲端沒設此變數，會自動跳過這一段、
        # 照常執行下方原本的 Ollama 邏輯（原始程式碼完整保留，未刪除）。
        # ============================================================
        if os.getenv("USE_GEMINI_CHAT", "0") == "1":
            convo = "\n".join(
                ("面試者：" if m["role"] == "user" else "面試官：") + m["content"]
                for m in messages_payload[1:]
            )
            g = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=system_prompt
                + "\n\n以下是目前的對話，請以面試官身分回覆最後一則，只輸出面試官要說的話：\n"
                + convo,
            )
            ai_response = (g.text or "").strip()
            if not ai_response:
                ai_response = "（面試官正看著你，似乎在等待更具體的回答...）"

            new_ai_msg = Model.ChatMessage(user_id=user.id, role="assistant", content=ai_response)
            db.add(new_ai_msg)
            db.commit()

            return {"response": ai_response}
        # 🆕 ===================== Gemini 分支結束 =====================

        ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        client = AsyncClient(host=ollama_host)

        response = await client.chat(
            model=model_name,
            messages=messages_payload,
            options={
                "temperature": 0.3,
                "num_predict": 1024,
                "top_k": 40,
                "top_p": 0.9,
            }
        )

        if 'message' in response and 'content' in response['message']:
            ai_response = response['message']['content']
            if not ai_response.strip():
                ai_response = "（面試官正看著你，似乎在等待更具體的回答...）"

            # 2️⃣ 將 AI 的回答也寫入資料庫，完成記憶閉環
            new_ai_msg = Model.ChatMessage(user_id=user.id, role="assistant", content=ai_response)
            db.add(new_ai_msg)
            db.commit()

            return {"response": ai_response}
        else:
            db.commit() # 仍提交使用者端訊息
            return {"response": "系統錯誤：面試官連線異常。"}

    except Exception as e:
        db.rollback() # 發生錯誤時回滾
        print(f"❌ 發生錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI 服務連線失敗: {str(e)}")
