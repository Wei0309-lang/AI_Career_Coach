import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. 優先讀取雲端環境變數，若在本地開發未設定，則自動切換回原本的 SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# 2. 建立引擎：動態判斷資料庫類型
if DATABASE_URL.startswith("sqlite"):
    # 如果是 SQLite，才需要 check_same_thread 參數
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # 雲端 Neon PostgreSQL 不需要 check_same_thread，直接連線即可
    engine = create_engine(DATABASE_URL)

# 3. 建立 SessionLocal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. 建立 Base
Base = declarative_base()