# AI Career Coach

AI 驅動的職涯輔助平台，提供 AI 模擬面試與履歷評鑑功能。

- **前端**：Next.js 16 + TypeScript
- **後端**：Python FastAPI
- **AI 面試**：Ollama 本地 LLM（llama-3-8b）
- **履歷評鑑**：Google Gemini API

> **注意**：Vercel、Render、Neon（雲端資料庫）、Resend（寄信服務）的帳號權限僅限專案負責人持有。
> 其他開發者請依照本文件在**本機**建立完整的獨立測試環境。

---

## 本地開發環境建置

### 前置需求

| 工具 | 版本 | 說明 |
|---|---|---|
| Python | 3.10+ | 後端執行環境 |
| Node.js | 18+ | 前端執行環境 |
| Git | 任意 | 版本控制 |
| DB Browser for SQLite | 最新版 | 手動驗證帳號用（見下方說明） |
| Ollama | 最新版 | AI 面試功能（選用） |

- DB Browser for SQLite 下載：https://sqlitebrowser.org
- Ollama 下載：https://ollama.com

---

### Step 1：Clone 專案

```bash
git clone https://github.com/Wei0309-lang/AI_Career_Coach.git
cd AI_Career_Coach
```

---

### Step 2：後端設定

```bash
# 建立虛擬環境
python -m venv .venv

# 啟動虛擬環境
# Windows：
.venv\Scripts\activate
# Mac / Linux：
source .venv/bin/activate

# 安裝套件
pip install -r requirements.txt
```

複製環境變數範本：

```bash
# Windows：
copy .env.example .env
# Mac / Linux：
cp .env.example .env
```

開啟 `.env`，依照下表填入：

| 變數 | 是否必填 | 說明 |
|---|---|---|
| `GEMINI_API_KEY` | **必填** | 見下方「取得 Gemini API Key」 |
| `ADMIN_SECRET` | 建議填 | 任意字串即可，例如 `local-dev-123` |
| `SMTP_PASSWORD` | **不需填** | 本地端繞過寄信流程（見下方說明） |

其餘變數保持 `.env.example` 的預設值即可。

#### 取得 Gemini API Key

1. 前往 https://aistudio.google.com
2. 登入 Google 帳號
3. 點選左側「Get API Key」→「Create API Key」
4. 複製產生的金鑰，貼入 `.env` 的 `GEMINI_API_KEY=` 後方

免費方案即可使用，不需綁定信用卡。

---

### Step 3：前端設定

```bash
cd frontend
npm install

# Windows：
copy .env.local.example .env.local
# Mac / Linux：
cp .env.local.example .env.local
```

`.env.local` 預設已指向 `http://localhost:8001`，本地開發**不需要修改**。

---

### Step 4：啟動服務

開啟**兩個**終端機視窗：

**終端機 1 — 後端（在根目錄執行）：**

```bash
python -m uvicorn Main:app --reload --port 8001 --env-file .env
```

出現 `Application startup complete.` 即代表後端啟動成功。

**終端機 2 — 前端（在 frontend/ 目錄執行）：**

```bash
cd frontend
npm run dev
```

瀏覽器開啟 `http://localhost:3000` 即可使用。

> **VS Code 使用者：** 按 `Ctrl+Shift+P` → `Run Task` → `Start All (Backend + Frontend)` 可一鍵同時啟動。

---

### Step 5：測試帳號註冊流程（重要）

本專案的信箱驗證功能依賴 Resend 服務，且寄件網域（`@cguimgraduatepj.me`）**僅限專案負責人的帳號才能使用**。其他開發者在本機測試時，系統雖然會完成帳號建立，但驗證信**不會寄出**，必須透過以下步驟手動開通帳號：

**5-1. 先到前端正常操作「註冊」**

填入 Email 與密碼後按下送出，系統回應「請至信箱驗證」即代表帳號已建立成功（忽略沒有收到信這件事）。

**5-2. 用 DB Browser for SQLite 手動開通帳號**

1. 開啟 DB Browser for SQLite
2. 點選「Open Database」，選取專案根目錄的 `app.db`
3. 切換到「Browse Data」頁籤，選擇 `user` 資料表
4. 找到剛才註冊的 Email 那一列
5. 將 `is_verified` 欄位的值從 `0` 改為 `1`
6. 點選上方「Write Changes」儲存

回到瀏覽器，即可用該帳號正常登入。

---

### Step 6：Ollama 模型設定（AI 面試功能）

> 此步驟僅影響 `/chat` AI 面試功能。跳過不影響登入、履歷評鑑等其他功能。

**6-1. 下載模型檔案（約 4.6 GB）**

前往以下連結下載 `llama-3-8b-instruct.Q4_K_M.gguf`：

https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf

下載完成後將檔案**重新命名為** `llama-3-8b-instruct.Q4_K_M.gguf`，放至專案**根目錄**（與 `Modelfile` 同層）。

**6-2. 建立 Ollama 模型**

確認 Ollama 已在背景執行後，在根目錄執行：

```bash
ollama create my-career-coach -f Modelfile
```

出現 `success` 即完成設定。重新整理瀏覽器後 AI 面試功能即可使用。

---

## 功能測試對照表

| 功能 | 本地可用 | 前置條件 | 注意事項 |
|---|---|---|---|
| 註冊帳號 | ✅ | 無 | 不會收到驗證信，需手動開通（Step 5） |
| 登入 | ✅ | 帳號已手動開通 | 無 |
| 履歷評鑑 | ✅ | 填入 `GEMINI_API_KEY` | 免費申請即可 |
| AI 面試（/chat） | ✅ | 完成 Step 6 | 需下載 4.6 GB 模型 |
| 信箱驗證信 | ❌ | 需 Resend 帳號與驗證網域 | 僅負責人可用，本地端以 Step 5 替代 |

---

## 常見問題

**Q：`pip install` 失敗或出現找不到套件的錯誤**

確認 Python 版本為 3.10 以上，且虛擬環境已啟動——提示字元最前面應出現 `(.venv)`。

**Q：後端啟動時出現 `GEMINI_API_KEY` 相關錯誤**

`.env` 檔案中的 `GEMINI_API_KEY` 未填入，或金鑰格式錯誤。請重新確認 Step 2。

**Q：`/chat` 功能回傳 500 錯誤**

可能原因有二：
1. Ollama 服務未在背景執行——開啟 Ollama 應用程式後再試
2. `my-career-coach` 模型尚未建立——重新執行 Step 6-2

**Q：DB Browser 找不到 `app.db`**

後端至少要啟動過一次，`app.db` 才會自動產生。請先完成 Step 4 啟動後端，再回來做 Step 5。
