from sqlalchemy import Column, String, Boolean, DateTime, Text
from datetime import datetime
import uuid
from Database import Base

class User(Base):
    __tablename__ = "users" # 資料庫裡的真實表名

    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    
    # 信件驗證相關欄位
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String, unique=True, index=True, nullable=True)

    # 履歷相關欄位
    full_name = Column(String, nullable=True)
    summary = Column(String, nullable=True)
    skills = Column(String, nullable=True)
    experience = Column(String, nullable=True)

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True)
    role = Column(String)
    content = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    session_id = Column(String, index=True, nullable=True)  # 所屬面試場次

# ===== 面試場次(v2 新增)=====
class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True)
    position = Column(String)          # 目標職位
    level = Column(String)             # 應徵級別
    status = Column(String, default="active")   # active / finished
    report_json = Column(Text, nullable=True)   # AI 評估報告(JSON 字串)
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)