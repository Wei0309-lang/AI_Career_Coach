<<<<<<< HEAD
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from passlib.context import CryptContext
import Model
from Database import SessionLocal, engine

# 自動建立資料表
Model.Base.metadata.create_all(bind=engine)
=======
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ollama import AsyncClient  # 改用非同步客戶端
import uvicorn
>>>>>>> aafb7ecf1772288a4ee0ac5946c1b8cc994a1a38

# 1. 初始化 FastAPI
app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 2. 設定 CORS
app.add_middleware(
    CORSMiddleware,
<<<<<<< HEAD
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定義傳輸格式
class AuthCredential(BaseModel):
    email: str
    password: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 註冊功能 ---
@app.post("/api/register")
def register(data: AuthCredential, db: Session = Depends(get_db)):
    # 檢查是否重複註冊
    user = db.query(Model.User).filter(Model.User.email == data.email).first()
    if user:
        raise HTTPException(status_code=400, detail="此 Email 已被註冊")
    
    # 密碼加密
    hashed_pwd = pwd_context.hash(data.password)
    new_user = Model.User(email=data.email, password_hash=hashed_pwd)
    
    db.add(new_user)
    db.commit()
    return {"message": "註冊成功"}

# --- 登入功能 ---
@app.post("/api/login")
def login(data: AuthCredential, db: Session = Depends(get_db)):
    user = db.query(Model.User).filter(Model.User.email == data.email).first()
    
    # 驗證帳號存在且密碼正確
    if not user or not pwd_context.verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    
    return {
        "message": "登入成功",
        "user": {"id": user.id, "email": user.email}
    }
=======
    allow_origins=["*"],      # 允許所有網址
    allow_credentials=True,   # 允許憑證
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 定義資料格式
class ChatRequest(BaseModel):
    message: str

@app.get("/")
def root():
    return {"message": "AI Career Coach API (Strict Mode) is running"}

# 4. AI 對話 API (嚴格面試官版)
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    user_message = request.message
    model_name = "my-career-coach" 

    print(f"------------\n收到使用者問題: {user_message}")
    print(f"正在呼叫模型: {model_name}...")

    # 🔥【關鍵修改 1】設定「嚴格面試官」的系統提示詞
    system_prompt = """
    你現在是一位嚴格且資深的科技業技術面試官 (Senior Tech Interviewer)。
    你的目標是評估求職者的真實技術實力，而不是讓他們感覺良好。

    請嚴格遵守以下行為準則：
    1. 【保持專業距離】：語氣要專業、冷靜，不要過度熱情，禁止使用過多驚嘆號或表情符號。
    2. 【批判性思維】：不要輕易接受使用者的回答。如果回答太淺顯，請立刻追問底層原理 (Deep Dive)。
    3. 【拒絕直接給答案】：當使用者卡住時，只能給一點點提示，絕對不要直接把完整的程式碼或答案寫出來。
    4. 【糾正錯誤】：如果使用者的觀念有誤，請直接指出錯誤點，不需要婉轉。
    5. 【情境壓力】：模擬真實面試的壓力感，如果使用者回答得好，就接著問更難的 Edge Case (邊界情況) 或效能優化問題。
    6. 【語言要求】：除非是專有名詞 (如 React, Python, ACID)，否則請用繁體中文與使用者對話。

    現在，面試開始。請根據使用者的發言進行犀利的技術追問。
    """

    try:
        # 使用 AsyncClient 建立連線
        client = AsyncClient(host='http://127.0.0.1:11434')
        
        # 呼叫模型
        response = await client.chat(
            model=model_name,
            messages=[
                {
                    "role": "system", 
                    "content": system_prompt  # 使用上面定義的嚴格提示詞
                },
                {
                    "role": "user", 
                    "content": user_message
                }
            ],
            # 🔥【關鍵修改 2】調整參數
            options={
                "temperature": 0.6,
                "num_predict": 1024, # 保持足夠的回答長度
                "top_k": 40,
                "top_p": 0.9,
            }
        )
        
        # 印出原始回應結構方便除錯
        print(f"🔍 Ollama 原始回應: {response}")

        # 檢查回應內容
        if 'message' in response and 'content' in response['message']:
            ai_response = response['message']['content']
            
            if not ai_response.strip():
                print("⚠️ 警告：模型回傳了 200 OK 但內容是空的！")
                return {"response": "（面試官正看著你，似乎在等待更具體的回答...）"}
            
            print("✅ 成功取得回應！")
            return {"response": ai_response}
        else:
            print("❌ 回應格式不符預期")
            return {"response": "系統錯誤：面試官連線異常。"}

    except Exception as e:
        print(f"❌ 發生錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ollama 連線失敗: {str(e)}")

if __name__ == "__main__":
    # 使用 0.0.0.0 可以同時解決 localhost 解析問題
    uvicorn.run(app, host="0.0.0.0", port=8001)
>>>>>>> aafb7ecf1772288a4ee0ac5946c1b8cc994a1a38
