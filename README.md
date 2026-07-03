# AI Career Coach（Huang 分支）

AI 驅動的職涯輔助平台，提供 AI 模擬面試與履歷評鑑功能。

- **前端**：Next.js 16 + TypeScript
- **後端**：Python FastAPI
- **登入/註冊**：Supabase Auth
- **AI 面試**：Ollama 本地 LLM（llama-3-8b）
- **履歷評鑑**：Google Gemini API
- **履歷 PDF/Word 上傳解析**：後端解析文字後由 Gemini 整理成結構化欄位

> **注意**：Vercel、Render、Neon（雲端資料庫）、Supabase、Resend（寄信服務）的帳號權限僅限專案負責人持有。
> 其他開發者請依照本文件在**本機**建立完整的獨立測試環境。

---

## 本分支相對 `master` 的改動

1. **登入/註冊系統整個換成 Supabase Auth**（原本是自建 email+密碼 + 手動用 Resend 寄驗證信）
   - 修正了原本的安全漏洞：舊版後端會直接信任前端傳來的 `user_id` 字串，任何人猜到別人的 ID 就能存取其資料。現在後端會驗證 Supabase 簽發的 JWT，從已驗證的身份取得使用者，不再信任前端傳入的 ID。
   - 註冊確認信、忘記密碼信改由 **Supabase Auth 觸發寄送，但實際寄送管道走 Resend**（在 Supabase Dashboard 設定自訂 SMTP 指向 Resend，沿用原本 `cguimgraduatepj.me` 網域寄件）。
   - 新增「忘記密碼」功能（`/reset-password` 頁面）。
   - Email 已註冊的提示沿用 Supabase 內建機制（註冊送出後才提示，非即時檢查）。
2. **新增履歷 PDF / Word 上傳解析功能**
   - 履歷頁面新增「上傳 PDF」「上傳 Word」兩個按鈕，上傳後由後端解析文字、丟給 Gemini 整理成結構化欄位，自動帶入既有表單（姓名/簡介/技能/經歷）。
   - **上傳的檔案本體不會被儲存**，解析完即丟棄，沒有使用 Supabase Storage，資料庫仍是 Neon（生產環境）/ SQLite（本地）。
   - 檔案格式限 `.pdf`、`.docx`，大小上限 10MB（可用 `MAX_RESUME_UPLOAD_MB` 環境變數調整）。
   - 履歷表單新增「未儲存變更」偵測：重複上傳、離開頁面前都會提醒尚未送出的內容。
3. **資料庫本身沒有換**，仍然是 Neon（生產）/ SQLite（本地），只有 `users` 表拿掉了密碼與驗證相關欄位（改由 Supabase 管理）。

---

## 本地開發環境建置

### 前置需求

| 工具 | 版本 | 說明 |
|---|---|---|
| Python | 3.10+ | 後端執行環境 |
| Node.js | 18+ | 前端執行環境 |
| Git | 任意 | 版本控制 |
| Supabase 帳號 | 免費方案即可 | 登入/註冊功能用，見下方說明 |
| DB Browser for SQLite | 最新版 | 排查本機資料庫問題用（選用） |
| Ollama | 最新版 | AI 面試功能（選用） |

- Supabase 註冊：https://supabase.com
- DB Browser for SQLite 下載：https://sqlitebrowser.org
- Ollama 下載：https://ollama.com

---

### Step 1：Clone 專案

```bash
git clone https://github.com/Wei0309-lang/AI_Career_Coach.git
cd AI_Career_Coach
git checkout Huang
```

---

### Step 2：準備 Supabase 專案

如果沒有專案負責人給的測試帳號，可自行申請免費方案建立一個新專案。

建立好後，到 Supabase Dashboard 設定：

1. **Authentication → URL Configuration → Redirect URLs**，加入 `http://localhost:3000/reset-password`（忘記密碼功能需要）
2. （可選，若要測試品牌化的驗證信）**Authentication → SMTP Settings**，改用 Resend 的 SMTP 資訊寄信
3. 到 **Settings → API** 頁面，記下 `Project URL` 與 `anon public key`，下一步會用到

---

### Step 3：後端設定

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
| `SUPABASE_URL` | **必填** | Step 2 記下的 Supabase Project URL，例如 `https://your-project-ref.supabase.co` |
| `ADMIN_SECRET` | 建議填 | 任意字串即可，例如 `local-dev-123` |
| `MAX_RESUME_UPLOAD_MB` | 選填 | 履歷檔案大小上限（MB），不填預設 10 |

其餘變數保持 `.env.example` 的預設值即可。

#### 取得 Gemini API Key

1. 前往 https://aistudio.google.com
2. 登入 Google 帳號
3. 點選左側「Get API Key」→「Create API Key」
4. 複製產生的金鑰，貼入 `.env` 的 `GEMINI_API_KEY=` 後方

免費方案即可使用，不需綁定信用卡。

---

### Step 4：前端設定

```bash
cd frontend
npm install

# Windows：
copy .env.local.example .env.local
# Mac / Linux：
cp .env.local.example .env.local
```

開啟 `frontend/.env.local`，依照下表填入：

| 變數 | 是否必填 | 說明 |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | 不需改 | 預設已指向 `http://localhost:8001` |
| `NEXT_PUBLIC_SUPABASE_URL` | **必填** | Step 2 記下的 Supabase Project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | **必填** | Step 2 記下的 anon public key |

`anon/public key` 設計上就是給前端公開使用的，可安全放在這裡；但 `.env`／`.env.local` 本身仍不可提交進 git（已在 `.gitignore` 排除）。

---

### Step 5：啟動服務

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

### Step 6：測試帳號註冊流程

信箱驗證完全由 Supabase 處理，不需要手動操作資料庫：

1. 在前端正常操作「註冊」，填入 Email 與密碼送出
2. 到收件信箱收驗證信（若尚未設定 Resend SMTP，會收到 Supabase 預設寄出的驗證信）
3. 點擊驗證連結後即可回到前端正常登入

---

### Step 7：Ollama 模型設定（AI 面試功能）

> 此步驟僅影響 `/chat` AI 面試功能。跳過不影響登入、履歷評鑑等其他功能。

**7-1. 下載模型檔案（約 4.6 GB）**

前往以下連結下載 `llama-3-8b-instruct.Q4_K_M.gguf`：

https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf

下載完成後將檔案**重新命名為** `llama-3-8b-instruct.Q4_K_M.gguf`，放至專案**根目錄**（與 `Modelfile` 同層）。

**7-2. 建立 Ollama 模型**

確認 Ollama 已在背景執行後，在根目錄執行：

```bash
ollama create my-career-coach -f Modelfile
```

出現 `success` 即完成設定。重新整理瀏覽器後 AI 面試功能即可使用。

---

## 功能測試對照表

| 功能 | 本地可用 | 前置條件 | 注意事項 |
|---|---|---|---|
| 註冊帳號 | ✅ | 已建立 Supabase 專案 | 驗證信由 Supabase 寄出（或轉走 Resend） |
| 登入 | ✅ | 帳號已完成信箱驗證 | 無 |
| 忘記密碼 | ✅ | Redirect URLs 已設定 `/reset-password` | 見 Step 2 |
| 履歷評鑑 | ✅ | 填入 `GEMINI_API_KEY` | 免費申請即可 |
| 履歷 PDF/Word 上傳解析 | ✅ | 填入 `GEMINI_API_KEY` | 檔案僅解析文字，不會被儲存 |
| AI 面試（/chat） | ✅ | 完成 Step 7 | 需下載 4.6 GB 模型 |

---

## API 變更對照（相對 `master` 分支）

| 項目 | master 分支 | Huang 分支 |
|---|---|---|
| `POST /api/register`、`POST /api/login`、`GET /api/verify` | 有 | **已移除**，改由前端直接呼叫 Supabase SDK |
| `GET /api/resume/{user_id}` | 路徑帶 `user_id` | **改成 `GET /api/resume`**，身份從 `Authorization: Bearer <token>` 取得 |
| `POST /api/resume` | body 需帶 `user_id` | body **不需要 `user_id`**，身份從 JWT 取得 |
| `POST /chat` | body 需帶 `user_id` | body **不需要 `user_id`**，身份從 JWT 取得 |
| `POST /api/resume/parse` | 沒有 | **新增**，上傳 PDF/Word 履歷檔案，回傳 AI 解析後的結構化欄位 |

呼叫任何受保護端點時，前端都要在 header 帶上 `Authorization: Bearer <session.access_token>`（`session` 來自 `supabase.auth.getSession()`）。

---

## 常見問題

**Q：`pip install` 失敗或出現找不到套件的錯誤**

確認 Python 版本為 3.10 以上，且虛擬環境已啟動——提示字元最前面應出現 `(.venv)`。

**Q：後端啟動時出現 `GEMINI_API_KEY` 相關錯誤**

`.env` 檔案中的 `GEMINI_API_KEY` 未填入，或金鑰格式錯誤。請重新確認 Step 3。

**Q：`/api/resume`、`/chat` 回傳 401**

多半是前端沒帶到 `Authorization` header，或後端 `SUPABASE_URL` 沒填對。確認：
1. 瀏覽器 Console 執行 `Object.keys(localStorage)`，應該要看到 `sb-<project-ref>-auth-token`
2. `.env` 的 `SUPABASE_URL` 跟 `frontend/.env.local` 的 `NEXT_PUBLIC_SUPABASE_URL` 是同一個值
3. 修改 `.env`／`.env.local` 後**務必完全重啟**對應的終端機（`Ctrl+C` 再重新執行），單純熱重載不會重新讀取環境變數

**Q：`/api/resume` 回傳 500，錯誤訊息提到 `NOT NULL constraint failed`**

代表本機 `app.db` 是舊版 `master` 分支的 schema（帶有 `is_verified`、`password_hash` 等欄位）。呼叫以下網址重置本機資料庫即可（只會清空本機測試資料，**不會影響 Supabase 帳號**，不需要重新註冊）：

```
http://localhost:8001/api/reset-db?secret=<你的 ADMIN_SECRET>
```

**Q：`/chat` 功能回傳 500 錯誤**

可能原因有二：
1. Ollama 服務未在背景執行——開啟 Ollama 應用程式後再試
2. `my-career-coach` 模型尚未建立——重新執行 Step 7-2
