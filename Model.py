from sqlalchemy import Column, String
import uuid
from Database import Base

class User(Base):
    __tablename__ = "users" # 資料庫裡的真實表名

    # 定義欄位
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    
    # 未來你可以繼續加：nickname = Column(String) 等等