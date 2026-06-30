from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from passlib.context import CryptContext
from ollama import AsyncClient
from google import genai
import uvicorn
import Model
from Database import SessionLocal, engine
import os
import uuid
import requests


# 自動建立資料表
Model.Base.metadata.create_all(bind=engine)

app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
gemini_client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

# 🌟 核心修正 1：升級 CORS 設定，用 regex 包容所有 Vercel 分支與預覽網址
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://ai-career-coach-gray-iota.vercel.app",
        "https://cguimgraduatepj.me",        # 
        "https://www.cguimgraduatepj.me"     # 
    ],
    allow_origin_regex=r"https://.*\.vercel\.app", # 允許任何 vercel.app 結尾的來源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AuthCredential(BaseModel):
    email: str
    password: str

class ChatRequest(BaseModel):
    user_id: str
    message: str

class ResumeData(BaseModel):
    user_id: str
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


# 🌟 核心修正 2：新增「重置資料庫」的 API (用來解決 f405 舊欄位衝突)
@app.get("/api/reset-db")
def reset_database():
    try:
        # 這會強制刪除舊有的資料表，並依照最新的 Model.py 重新建立完整欄位
        Model.Base.metadata.drop_all(bind=engine)
        Model.Base.metadata.create_all(bind=engine)
        return {"message": "✅ 資料庫已成功重置更新！請回到前端重新註冊帳號。"}
    except Exception as e:
        return {"message": f"❌ 重置失敗: {str(e)}"}


# 非同步寄送驗證信件函數
# 非同步寄送驗證信件函數 (改為 Resend HTTP API 版本)
def send_verification_email(email: str, token: str):
    # 組裝驗證連結
    backend_base = os.getenv("BACKEND_URL", "http://localhost:8001")
    verify_url = f"{backend_base}/api/verify?token={token}"
    
    print(f"\n==================================================")
    print(f"✉️  準備向 {email} 發送驗證信 (透過 Resend API)")
    print(f"🔗 驗證連結: {verify_url}")
    print(f"==================================================\n")

    # 讀取環境變數 (直接使用你的 Resend API Key)
    RESEND_API_KEY = os.getenv("SMTP_PASSWORD") 
    
    # 🌟 這裡是你剛申請的專屬網域信箱 (請確認 Render 上有設定這個變數)
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "noreply@cguimgraduatepj.me")

    if not RESEND_API_KEY:
        print("❌ 寄信失敗: 找不到 Resend API Key，請檢查環境變數 SMTP_PASSWORD")
        return

    # 設定 API 標頭
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }

    # 設定寄件內容 (支援 HTML 美化)
    payload = {
        "from": f"AI Career Coach <{SMTP_FROM_EMAIL}>",
        "to": [email],
        "subject": "AI Career Coach 帳號驗證信",
        "html": f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e9e9e9; border-radius: 10px;">
            <h2 style="color: #333; text-align: center;">🎉 歡迎註冊 AI Career Coach！</h2>
            <p>您好：</p>
            <p>感謝您使用本系統。請點擊下方按鈕以啟用您的帳號，開啟您的 AI 模擬面試之旅：</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verify_url}" style="display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">點我驗證並開通帳號</a>
            </div>
            <p style="color: #666; font-size: 14px;">如果按鈕無法點擊，您也可以複製此連結至瀏覽器開啟：</p>
            <p style="color: #007bff; font-size: 14px; word-break: break-all;">{verify_url}</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;" />
            <p style="color: #999; font-size: 12px; text-align: center;">如果您沒有註冊此網站，請忽略此郵件。</p>
        </div>
        """
    }

    try:
        # 向 Resend 發送 POST 請求 (走 443 網頁通道，絕對不會被 Render 擋)
        response = requests.post("https://api.resend.com/emails", headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            print(f"✅ 郵件成功經由 Resend API 發送至 {email}")
        else:
            print(f"❌ 郵件 API 發送失敗: 狀態碼 {response.status_code}, 錯誤訊息: {response.text}")
    except Exception as e:
        print(f"❌ 郵件 API 連線發生異常錯誤: {str(e)}")


@app.get("/")
def root():
    return {"message": "AI Career Coach API is running"}


# --- 註冊功能 ---
@app.post("/api/register")
def register(data: AuthCredential, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(Model.User).filter(Model.User.email == data.email).first()
    if user:
        raise HTTPException(status_code=400, detail="此 Email 已被註冊")
    
    hashed_pwd = pwd_context.hash(data.password)
    verification_token = str(uuid.uuid4())
    
    new_user = Model.User(
        email=data.email, 
        password_hash=hashed_pwd,
        is_verified=False,
        verification_token=verification_token
    )
    
    db.add(new_user)
    db.commit()
    
    background_tasks.add_task(send_verification_email, data.email, verification_token)
    return {"message": "註冊成功！請檢查您的信箱並點擊驗證連結完成開通。"}

# 🌟 新增：讀取現有履歷資料的 API
@app.get("/api/resume/{user_id}")
def get_resume(user_id: str, db: Session = Depends(get_db)):
    user = db.query(Model.User).filter(Model.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="找不到使用者")
    
    # 將資料庫中的內容回傳給前端，若為 None 則給予空字串避免前端 input 報錯
    return {
        "fullName": user.full_name or "",
        "summary": user.summary or "",
        "skills": user.skills or "",
        "experience": user.experience or ""
    }

# 驗證信箱端點
@app.get("/api/verify", response_class=HTMLResponse)
def verify(token: str, db: Session = Depends(get_db)):
    user = db.query(Model.User).filter(Model.User.verification_token == token).first()
    
    if not user:
        return """
        <html>
            <body style="text-align: center; margin-top: 50px; font-family: sans-serif;">
                <h2 style="color: #dc3545;">❌ 驗證失敗</h2>
                <p>無效的驗證代碼或此連結已失效。</p>
            </body>
        </html>
        """
        
    user.is_verified = True
    user.verification_token = None
    db.commit()
    
    # 這裡的超連結會自動引導使用者回到 Next.js 前端網頁
    return """
    <html>
        <body style="text-align: center; margin-top: 50px; font-family: sans-serif;">
            <h2 style="color: #28a745;">🎉 驗證成功！</h2>
            <p>您的帳號已成功啟用，現在可以返回首頁登入系統了。</p>
            <br/>
            <a href="https://ai-career-coach-gray-iota.vercel.app" style="padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回登入頁面</a>
        </body>
    </html>
    """


# --- 登入功能 ---
@app.post("/api/login")
def login(data: AuthCredential, db: Session = Depends(get_db)):
    user = db.query(Model.User).filter(Model.User.email == data.email).first()
    
    if not user or not pwd_context.verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="此帳號尚未完成信件認證，請先至信箱收取驗證信開通。")
    
    return {
        "message": "登入成功",
        "user": {"id": user.id, "email": user.email}
    }


# --- 🌟 新增：履歷整合 API（從 Huang 分支轉換移植） ---
@app.post("/api/resume")
def submit_resume(data: ResumeData, db: Session = Depends(get_db)):
    user = db.query(Model.User).filter(Model.User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="找不到使用者")
    
    # 存入資料庫以供後續 AI 面試官參考
    user.full_name = data.fullName
    user.summary = data.summary
    user.skills = data.skills
    user.experience = data.experience
    db.commit()

    prompt = f"""你是一位專業的履歷顧問。請根據以下這份履歷,給出具體、可執行的改善建議。
請用繁體中文,條列 3-5 點重點,語氣專業但友善。

【個人簡介】
{data.summary}

【專業技能】
{data.skills}

【工作經歷】
{data.experience}

請針對內容的具體性、量化成就、技能呈現等面向給建議。"""

    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        suggestion = response.text
    except Exception as e:
        print(f"AI 呼叫失敗: {e}")
        suggestion = f"AI 服務暫時無法使用，錯誤訊息: {e}"

    return {"suggestion": suggestion}


# --- 🌟 升級：AI 對話 API (嚴格面試官版 - 包含履歷內容與對話記憶) ---
@app.post("/chat")
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    user_message = request.message
    model_name = "my-career-coach"
    
    # 查詢當前使用者與其履歷
    user = db.query(Model.User).filter(Model.User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")

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
        raise HTTPException(status_code=500, detail=f"Ollama 連線失敗: {str(e)}")