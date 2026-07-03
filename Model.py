from sqlalchemy import Column, String, DateTime
import datetime
import uuid
from Database import Base

class User(Base):
    __tablename__ = "users" # 資料庫裡的真實表名

    # id 對應 Supabase Auth 核發的使用者 UUID（不再由本地自行產生）
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=True)

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
    created_at = Column(DateTime, default=datetime.datetime.utcnow)