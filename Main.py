from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from passlib.context import CryptContext
from ollama import AsyncClient  # 載入 Ollama 非同步套件
import uvicorn
import Model
from Database import SessionLocal, engine
import os

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

@app.get("/")
def root():
    return {"message": "AI Career Coach API is running"}

# --- 註冊與登入功能 ---
@app.post("/api/register")
def register(data: AuthCredential, db: Session = Depends(get_db)):
    user = db.query(Model.User).filter(Model.User.email == data.email).first()
    if user:
        raise HTTPException(status_code=400, detail="此 Email 已被註冊")
    
    hashed_pwd = pwd_context.hash(data.password)
    new_user = Model.User(email=data.email, password_hash=hashed_pwd)
    
    db.add(new_user)
    db.commit()
    return {"message": "註冊成功"}
@app.post("/api/login")
def login(data: AuthCredential, db: Session = Depends(get_db)):
    user = db.query(Model.User).filter(Model.User.email == data.email).first()
    
    # 檢查帳號是否存在，以及密碼是否正確
    if not user or not pwd_context.verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    
    return {
        "message": "登入成功",
        "user": {"id": user.id, "email": user.email}
    }

# --- 4. AI 對話 API (嚴格面試官版 - 強制中文) ---
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    user_message = request.message
    # 🌟 修改 1：把 :latest 拿掉，直接呼叫 ollama3 比較安全
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
                # 修復核心 A：加上 role="system"，把面試官大腦設定灌進去！
                {"role": "system", "content": system_prompt},
                
                # 修復核心 B：這裡要改成 enforced_user_message，把加料的訊息傳出去！
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