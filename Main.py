from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from passlib.context import CryptContext
from ollama import AsyncClient  # 載入 Ollama 非同步套件
import uvicorn
import Model
from Database import SessionLocal, engine
import os
import uuid
import smtplib
from email.mime.text import MIMEText

# 自動建立資料表
Model.Base.metadata.create_all(bind=engine)

# 1. 初始化 FastAPI
app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 2. 設定 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定義資料格式
class AuthCredential(BaseModel):
    email: str
    password: str

class ChatRequest(BaseModel):
    message: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 🌟 新增：非同步寄送驗證信件函數
def send_verification_email(email: str, token: str):
    # 填入您的前端或後端驗證 URL（此處指向後端驗證端點）
    verify_url = f"http://localhost:8001/api/verify?token={token}"
    
    # [開發測試模式] 同步輸出到終端機，方便免設定 SMTP 直接測試流程
    print(f"\n==================================================")
    1681285324
    print(f"✉️  已向 {email} 發送驗證信！")
    print(f"🔗 測試驗證連結: {verify_url}")
    print(f"==================================================\n")

    # [正式生產模式環境變數設定] 如果有填寫環境變數，則啟動真實發信
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = os.getenv("SMTP_PORT", "587")
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

    if SMTP_HOST and SMTP_USER and SMTP_PASSWORD:
        try:
            msg = MIMEText(f"您好：\n\n感謝您註冊 AI Career Coach！請點擊下方連結啟用您的帳號：\n{verify_url}\n\n如果您沒有註冊此網站，請忽略此郵件。", "plain", "utf-8")
            msg["Subject"] = "AI Career Coach 帳號驗證信"
            msg["From"] = SMTP_USER
            msg["To"] = email

            with smtplib.SMTP(SMTP_HOST, int(SMTP_PORT)) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
            print(f"✅ 郵件成功經由 SMTP 發送至 {email}")
        except Exception as e:
            print(f"❌ 郵件發送失敗: {str(e)}")


@app.get("/")
def root():
    return {"message": "AI Career Coach API is running"}


# --- 註冊功能 (新增信件憑證生成) ---
@app.post("/api/register")
def register(data: AuthCredential, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(Model.User).filter(Model.User.email == data.email).first()
    if user:
        raise HTTPException(status_code=400, detail="此 Email 已被註冊")
    
    hashed_pwd = pwd_context.hash(data.password)
    verification_token = str(uuid.uuid4()) # 生成唯一的驗證 Token
    
    new_user = Model.User(
        email=data.email, 
        password_hash=hashed_pwd,
        is_verified=False, # 預設為未驗證
        verification_token=verification_token
    )
    
    db.add(new_user)
    db.commit()
    
    # 使用背景任務非同步寄信，不卡住前端排隊時間
    background_tasks.add_task(send_verification_email, data.email, verification_token)
    
    return {"message": "註冊成功！請檢查您的信箱並點擊驗證連結完成開通。"}


# 🌟 新增：驗證信箱端點
@app.get("/api/verify", response_class=HTMLResponse)
def verify(token: str, db: Session = Depends(get_db)):
    user = db.query(Model.User).filter(Model.User.verification_token == token).first()
    
    if not user:
        return """
        <html>
            <body style="text-align: center; margin-top: 50px; font-family: sans-serif;">
                <h2 style="color: #dc3545;">❌ 驗證失敗</h2>
                <p>無效的驗證代碼或此連結已失效。</p>
             body>
         html>
        """
        
    user.is_verified = True
    user.verification_token = None # 驗證成功後清除 Token，防止重複點擊
    db.commit()
    
    return """
    <html>
        <body style="text-align: center; margin-top: 50px; font-family: sans-serif;">
            <h2 style="color: #28a745;">🎉 驗證成功！</h2>
            <p>您的帳號已成功啟用，現在可以返回首頁登入系統了。</p>
            <br/>
            <a href="http://localhost:3000" style="padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">返回登入頁面</a>
         body>
     html>
    """


# --- 登入功能 (加入啟用狀態檢查) ---
@app.post("/api/login")
def login(data: AuthCredential, db: Session = Depends(get_db)):
    user = db.query(Model.User).filter(Model.User.email == data.email).first()
    
    # 檢查帳號是否存在，以及密碼是否正確
    if not user or not pwd_context.verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    
    # 🌟 新增：檢查帳號是否完成信件開通
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="此帳號尚未完成信件認證，請先至信箱收取驗證信開通。")
    
    return {
        "message": "登入成功",
        "user": {"id": user.id, "email": user.email}
    }


# --- AI 對話 API ---
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    user_message = request.message
    model_name = "my-career-coach"
    
    print(f"------------\n收到使用者問題: {user_message}")
  
    system_prompt = """
    【最高指導原則】：你必須、絕對只能使用「繁體中文 (Traditional Chinese)」回答。嚴禁使用英文或其他語言作為主要溝通語言（技術專有名詞如 React, API, Python 除外）。如果你使用英文回答，系統將會崩潰。

    你現在是一位嚴格且資深的科技業技術面試官 (Senior Tech Interviewer)。你的目標是評估求職者的真實技術實力。

    請嚴格遵守以下行為準則：
    1. 【保持專業距離】：語氣要專業、冷靜，不要過度熱情。
    2. 【批判性思維】：不要輕易接受使用者的回答，請立刻追問底層原理。
    3. 【拒絕直接給答案】：當使用者卡住時，只能給提示，絕對不要直接寫出完整答案。
    4. 【糾正錯誤】：觀念有誤請直接指出錯誤點。
    """

    enforced_user_message = f"{user_message}\n\n(系統提示：請務必只使用繁體中文扮演面試官回覆)"

    try:
        ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        client = AsyncClient(host=ollama_host)
        
        response = await client.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": enforced_user_message} 
            ],
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
                return {"response": "（面試官正看著你，似乎在等待更具體的回答...）"}
            return {"response": ai_response}
        else:
            return {"response": "系統錯誤：面試官連線異常。"}

    except Exception as e:
        print(f"❌ 發生錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ollama 連線失敗: {str(e)}")