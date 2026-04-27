from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from passlib.context import CryptContext
import Model
from Database import SessionLocal, engine

# 自動建立資料表
Model.Base.metadata.create_all(bind=engine)

app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app.add_middleware(
    CORSMiddleware,
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