# AI Career Coach

AI 驅動的職涯輔助平台，提供 AI 模擬面試與履歷評鑑功能。

- **前端**：Next.js 16 + TypeScript，部署於 Vercel
- **後端**：Python FastAPI，部署於 Render
- **AI 面試**：Ollama 本地 LLM（llama-3-8b）
- **履歷評鑑**：Google Gemini API

---

## 本地開發環境建置

### 前置需求

| 工具 | 版本 | 說明 |
|---|---|---|
| Python | 3.10+ | 後端執行環境 |
| Node.js | 18+ | 前端執行環境 |
| Git | 任意 | 版本控制 |
| Ollama | 最新版 | AI 面試功能（選用） |

Ollama 下載：https://ollama.com

---

### Step 1：Clone 專案

```bash
git clone https://github.com/Wei0309-lang/AI_Career_Coach.git
cd AI_Career_Coach
```

---

### Step 2：後端設定

```bash
# 建立並啟動虛擬環境
python -m venv .venv

# Windows
.venv\Scripts\activate
# Mac / Linux
source .venv/bin/activate

# 安裝套件
pip install -r requirements.txt
```

複製環境變數範本並填入金鑰：

```bash
cp .env.example .env
```

開啟 `.env`，至少填入以下欄位：

| 變數 | 說明 | 取得方式 |
|---|---|---|
| `GEMINI_API_KEY` | 必填 | [aistudio.google.com](https://aistudio.google.com) 免費申請 |
| `SMTP_PASSWORD` | 選填 | Resend API Key，沒填則不寄驗證信 |
| `ADMIN_SECRET` | 建議填 | 任意字串，用於保護資料庫重置功能 |

其餘變數保持預設值即可。

---

### Step 3：前端設定

```bash
cd frontend
npm install
cp .env.local.example .env.local
```

`.env.local` 預設已指向 `http://localhost:8001`，本地開發不需要修改。

---

### Step 4：Ollama 模型設定（AI 面試功能）

> 跳過此步驟不影響登入、註冊、履歷評鑑等功能，僅 `/chat` 無法使用。

**4-1. 下載模型檔案**

前往 Hugging Face 搜尋 `llama-3-8b-instruct Q4_K_M gguf`，下載 `llama-3-8b-instruct.Q4_K_M.gguf`，放至專案**根目錄**（與 `Modelfile` 同層）。

**4-2. 建立 Ollama 模型**

```bash
ollama create my-career-coach -f Modelfile
```

---

### Step 5：啟動服務

開啟兩個終端機視窗分別執行：

**後端（在根目錄執行）：**

```bash
python -m uvicorn Main:app --reload --port 8001 --env-file .env
```

**前端（在 frontend/ 目錄執行）：**

```bash
npm run dev
```

瀏覽器開啟 `http://localhost:3000` 即可使用。

**VS Code 使用者：** 按 `Ctrl+Shift+P` → `Run Task` → `Start All (Backend + Frontend)` 一鍵啟動。

---

### 常見問題

**Q：註冊後無法登入，提示「尚未完成信件認證」**

未設定 `SMTP_PASSWORD` 時不會寄出驗證信。有兩個解法：

1. 在 [resend.com](https://resend.com) 申請免費帳號，每月 100 封免費，將 API Key 填入 `SMTP_PASSWORD`
2. 用 SQLite 工具（如 DB Browser for SQLite）開啟 `app.db`，將對應帳號的 `is_verified` 欄位改為 `1`

**Q：`/chat` 功能回傳 500 錯誤**

Ollama 服務未啟動，或 `my-career-coach` 模型尚未建立。確認 Ollama 已在背景執行，並完成 Step 4。

**Q：`pip install` 失敗**

確認 Python 版本為 3.10 以上，且虛擬環境已啟動（提示字元前應有 `(.venv)`）。
