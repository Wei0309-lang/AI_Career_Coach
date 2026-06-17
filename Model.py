from sqlalchemy import Column, String, Boolean
import uuid
from Database import Base

class User(Base):
    __tablename__ = "users" # 資料庫裡的真實表名

    # 定義欄位
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    
    # 🌟 新增：信件驗證相關欄位
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String, unique=True, index=True, nullable=True)