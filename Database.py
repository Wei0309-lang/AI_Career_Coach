from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. 指定 SQLite 資料庫檔案名稱 (它會自動在專案目錄下產生 app.db)
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

# 2. 建立引擎 (check_same_thread=False 是 SQLite 在 FastAPI 中必加的設定)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 3. 建立 SessionLocal，這是用來跟資料庫對話的「連線通行證」
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. 建立 Base，我們之後的資料表都要繼承它
Base = declarative_base()