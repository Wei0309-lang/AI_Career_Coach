from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from ollama import AsyncClient
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
import Model
from Database import engine
from auth import get_db, get_current_user
from rate_limit import rate_limited
import os
import io
import json
import hmac
import logging
from avatar import router as avatar_router
from heygen import router as heygen_router
from interview import router as interview_router
from resume_utils import flatten_resume_value

# 錯誤細節(例外內容、第三方 API 回應)只寫進伺服器 log(Render → Logs)，不回傳給使用者
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


# 自動建立資料表
Model.Base.metadata.create_all(bind=engine)

app = FastAPI()
gemini_client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

# --- 可移植性設定：從環境變數讀取，方便在不同環境部署 ---
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "my-career-coach")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")
# /api/reset-db 會刪光所有資料，平常一律關閉；需要重建 schema 時才在環境變數暫時設為 1
ALLOW_DB_RESET = os.getenv("ALLOW_DB_RESET", "0") == "1"
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]
MAX_RESUME_UPLOAD_MB = int(os.getenv("MAX_RESUME_UPLOAD_MB", "10"))

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

class ChatRequest(BaseModel):
    message: str

class ResumeData(BaseModel):
    fullName: str
    summary: str
    skills: str
    experience: str

    # 儲存履歷是系統邊界，不管上游(舊的前端快取狀態、AI 解析結果等)送來
    # 陣列/物件/null，一律攤平成文字，避免直接 422 擋下使用者的儲存操作
    @field_validator("fullName", "summary", "skills", "experience", mode="before")
    @classmethod
    def _coerce_to_text(cls, v):
        return flatten_resume_value(v)


# 「重置資料庫」的 API (用來解決舊欄位衝突，會刪光所有資料)
# 三道防護：
#   1. 環境變數 ALLOW_DB_RESET=1 才存在，否則一律 404(平常就關著，用完記得關回去)
#   2. 只接受 POST，瀏覽器網址列、爬蟲、連結預覽都不會誤觸
#   3. secret 放在 X-Admin-Secret header，不放網址(網址會被記進各種存取 log)
# 用法：curl -X POST https://<後端網址>/api/reset-db -H "X-Admin-Secret: <ADMIN_SECRET>"
@app.post("/api/reset-db")
def reset_database(x_admin_secret: str = Header("")):
    if not ALLOW_DB_RESET:
        raise HTTPException(status_code=404, detail="Not Found")
    if not ADMIN_SECRET or not hmac.compare_digest(x_admin_secret.encode(), ADMIN_SECRET.encode()):
        raise HTTPException(status_code=403, detail="禁止存取：缺少或錯誤的 secret")
    try:
        # 這會強制刪除舊有的資料表，並依照最新的 Model.py 重新建立完整欄位
        Model.Base.metadata.drop_all(bind=engine)
        Model.Base.metadata.create_all(bind=engine)
        logger.warning("資料庫已透過 /api/reset-db 重置")
        return {"message": "✅ 資料庫已成功重置更新！請回到前端重新註冊帳號。"}
    except Exception:
        logger.exception("資料庫重置失敗")
        raise HTTPException(status_code=500, detail="資料庫重置失敗，詳細原因請查看伺服器 log")


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
    """抽出 Word 裡所有文字：內文、表格(含巢狀表格)、文字方塊、頁首與頁尾。
    很多履歷範本整份內容都放在表格或文字方塊裡，只讀 document.paragraphs(只含內文最外層段落)
    會幾乎抽不到字，Gemini 拿到殘缺內容常回說明文字而非 JSON，導致解析失敗。"""
    document = Document(io.BytesIO(content))
    containers = [document.element.body]
    for section in document.sections:
        for part in (section.header, section.first_page_header, section.even_page_header,
                     section.footer, section.first_page_footer, section.even_page_footer):
            # 沿用前一節的頁首頁尾沒有自己的內容；直接讀 _element 會替它新建一份空白定義
            if not part.is_linked_to_previous:
                containers.append(part._element)

    lines: list[str] = []
    seen: set[str] = set()
    for container in containers:
        # iter 會依文件順序走到所有層級的段落(表格儲存格、文字方塊裡的段落都是 w:p)
        for p in container.iter(qn("w:p")):
            text = Paragraph(p, document).text.strip()
            # 文字方塊在 Word 檔裡常存兩份(新版格式 + 相容舊版的備援)，去除重複行
            if text and text not in seen:
                seen.add(text)
                lines.append(text)
    return "\n".join(lines)


# --- 履歷檔案上傳解析 API（PDF / Word，解析完即丟棄檔案本體，不做任何儲存）---
# 用一般 def 而非 async def：PDF/Word 解析與 Gemini 呼叫都是同步阻塞的，
# 寫成 async def 會卡住 event loop，解析履歷的那幾秒內其他所有請求都得排隊；
# 一般 def 會被 FastAPI 丟到 threadpool 執行，不影響其他請求
@app.post("/api/resume/parse")
def parse_resume_file(file: UploadFile = File(...), user: Model.User = Depends(rate_limited("resume_parse"))):
    filename = (file.filename or "").lower()
    if filename.endswith(".pdf"):
        file_kind = "pdf"
    elif filename.endswith(".docx"):
        file_kind = "docx"
    else:
        raise HTTPException(status_code=400, detail="僅支援 PDF 或 Word(.docx) 檔案")

    max_bytes = MAX_RESUME_UPLOAD_MB * 1024 * 1024
    size_error = HTTPException(status_code=400, detail=f"檔案大小超過 {MAX_RESUME_UPLOAD_MB}MB 上限")
    # 大檔案在 multipart 解析時已暫存到磁碟，先看大小就擋，不把整個檔案讀進記憶體
    if file.size is not None and file.size > max_bytes:
        raise size_error
    # 保底：拿不到大小時最多只讀上限 + 1 byte，超過就判定過大
    content = file.file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise size_error

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
每個欄位的值都必須是「單一純文字字串」，不可以是陣列或巢狀物件；
多筆技能或多段經歷請自行整理成一段連貫文字（可用頓號、換行分隔），不要拆成 JSON 陣列或子物件。
若原文中找不到某欄位對應的資訊，該欄位請回傳空字串。
只回傳 JSON 本身，不要加上任何說明文字或 markdown 標記。

【履歷原文】
{raw_text}
"""

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            # 強制只輸出 JSON；不加的話，內容不完整時 Gemini 常改回一段說明文字而導致解析失敗
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        raw_json = (response.text or "").replace("```json", "").replace("```", "").strip()
        start, end = raw_json.find("{"), raw_json.rfind("}")
        parsed = json.loads(raw_json[start:end + 1] if start != -1 and end > start else raw_json)
        if not isinstance(parsed, dict):
            raise ValueError(f"履歷解析結果不是 JSON 物件: {raw_json[:200]}")
    except Exception:
        logger.exception("履歷 AI 解析失敗")
        raise HTTPException(status_code=502, detail="AI 解析履歷內容失敗，請稍後再試")

    return {
        "fullName": flatten_resume_value(parsed.get("fullName")),
        "summary": flatten_resume_value(parsed.get("summary")),
        "skills": flatten_resume_value(parsed.get("skills")),
        "experience": flatten_resume_value(parsed.get("experience")),
    }


# --- 履歷整合 API ---
@app.post("/api/resume")
def submit_resume(data: ResumeData, user: Model.User = Depends(rate_limited("resume_submit")), db: Session = Depends(get_db)):
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
    except Exception:
        # 履歷本身已經存檔成功，只是拿不到建議，所以仍回 200，但不把例外內容顯示給使用者
        logger.exception("履歷健檢 AI 呼叫失敗")
        suggestion = "✅ 履歷已儲存，但 AI 健檢服務暫時無法使用，請稍後再按一次取得建議。"

    return {"suggestion": suggestion}


# --- AI 對話 API (嚴格面試官版 - 包含履歷內容與對話記憶) ---
@app.post("/chat")
async def chat_endpoint(request: ChatRequest, user: Model.User = Depends(rate_limited("legacy_chat")), db: Session = Depends(get_db)):
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
    #    (先倒序取 10 筆再反轉回時間順序；正序 limit 會拿到最舊的 10 筆)
    history_records = db.query(Model.ChatMessage)\
                        .filter(Model.ChatMessage.user_id == user.id)\
                        .order_by(Model.ChatMessage.created_at.desc())\
                        .limit(10).all()[::-1]

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
            # 這個端點是 async def，要用非同步的 client.aio，否則等 Gemini 回覆時會卡住整個 event loop
            g = await gemini_client.aio.models.generate_content(
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

    except Exception:
        db.rollback() # 發生錯誤時回滾
        logger.exception("/chat AI 呼叫失敗")
        raise HTTPException(status_code=500, detail="AI 服務連線失敗，請稍後再試")
