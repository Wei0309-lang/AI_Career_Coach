# AI Career Coach — Huang 分支說明

本分支在 `master` 的基礎上做了以下重構與新功能，**環境設定跟 `master` 分支不完全相同**，請照本文件設定，不要直接套用主 `README.md` 的步驟。

---

## 這個分支改了什麼

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

## 跟 `master` 分支的環境變數差異

### 後端 `.env`

| 變數 | master 分支 | Huang 分支 |
|---|---|---|
| `SMTP_PASSWORD` / `SMTP_FROM_EMAIL` | 需要（後端直接呼叫 Resend API 寄信） | **移除**（改由 Supabase Auth 觸發，Resend SMTP 設定在 Supabase Dashboard） |
| `FRONTEND_URL` / `BACKEND_URL` | 需要（組驗證信連結用） | **移除**（不再需要，Supabase 自己處理驗證/重設連結） |
| `SUPABASE_URL` | 沒有 | **新增**，例如 `https://your-project-ref.supabase.co`（後端用來抓 JWKS 公鑰驗證 JWT，非機密） |
| `MAX_RESUME_UPLOAD_MB` | 沒有 | 新增（選填，預設 10） |
| `DATABASE_URL` / `GEMINI_API_KEY` / `GEMINI_MODEL` / `ADMIN_SECRET` / `OLLAMA_HOST` / `OLLAMA_MODEL` / `ALLOWED_ORIGINS` | 需要 | 不變 |

### 前端 `frontend/.env.local`

| 變數 | master 分支 | Huang 分支 |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | 需要 | 不變 |
| `NEXT_PUBLIC_SUPABASE_URL` | 沒有 | **新增** |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | 沒有 | **新增** |

`NEXT_PUBLIC_SUPABASE_URL`、`NEXT_PUBLIC_SUPABASE_ANON_KEY` 在 Supabase Dashboard 的 **Settings → API** 頁面可以找到（anon/public key 設計上就是給前端公開用的，可安全放這裡）。

`SUPABASE_URL` 也不是機密資訊（跟前端那組 URL 是同一個值），但 `.env`／`.env.local` 本身仍不可提交進 git（已在 `.gitignore` 排除）。

---

## 本地開發設定步驟（本分支專屬）

除了主 `README.md` 的 Step 1~4（clone、Python/Node 環境、安裝套件）都一樣之外，額外需要：

1. **準備一個 Supabase 專案**（如果沒有專案負責人給的測試帳號，可自行申請免費方案建立一個新專案）
2. 在 Supabase Dashboard 設定：
   - **Authentication → URL Configuration → Redirect URLs**，加入 `http://localhost:3000/reset-password`（忘記密碼功能需要，正式環境要另外加上正式網域）
   - （可選，若要測試 Resend 寄信）**Authentication → SMTP Settings**，改用 Resend 的 SMTP 資訊
3. 後端 `.env` 依照上面表格，把 `SUPABASE_URL` 填入你的 Supabase 專案 URL，其餘照 `.env.example` 填
4. 前端 `frontend/.env.local` 依照上面表格，填入 `NEXT_PUBLIC_SUPABASE_URL`、`NEXT_PUBLIC_SUPABASE_ANON_KEY`
5. 啟動方式跟主 `README.md` 完全相同（兩個終端機分別跑後端 `uvicorn` 與前端 `npm run dev`）

### 測試帳號註冊流程（跟主 README 不同）

本分支的信箱驗證完全由 Supabase 處理，**不再需要用 DB Browser 手動把 `is_verified` 改成 1**：

1. 在前端正常註冊帳號
2. 到 Supabase 專案設定的收件信箱收驗證信（若尚未設定 Resend SMTP，會收到 Supabase 預設寄出的驗證信）
3. 點擊驗證連結後即可正常登入

---

## API 變更對照

| 項目 | master 分支 | Huang 分支 |
|---|---|---|
| `POST /api/register`、`POST /api/login`、`GET /api/verify` | 有 | **已移除**，改由前端直接呼叫 Supabase SDK |
| `GET /api/resume/{user_id}` | 路徑帶 `user_id` | **改成 `GET /api/resume`**，身份從 `Authorization: Bearer <token>` 取得 |
| `POST /api/resume` | body 需帶 `user_id` | body **不需要 `user_id`**，身份從 JWT 取得 |
| `POST /chat` | body 需帶 `user_id` | body **不需要 `user_id`**，身份從 JWT 取得 |
| `POST /api/resume/parse` | 沒有 | **新增**，上傳 PDF/Word 履歷檔案，回傳 AI 解析後的結構化欄位 |

呼叫任何受保護端點時，前端都要在 header 帶上 `Authorization: Bearer <session.access_token>`（`session` 來自 `supabase.auth.getSession()`）。

---

## 已知本機注意事項

- 如果你的本機 `app.db` 是很早之前、還在用 `master` 分支的舊 schema 建立的（帶有 `is_verified`、`password_hash` 等欄位），啟動本分支後可能會遇到 `NOT NULL constraint failed` 之類的錯誤。這是因為 SQLAlchemy 的 `create_all()` 不會自動幫舊表改欄位。
  - 解法：呼叫 `http://localhost:8001/api/reset-db?secret=<你的 ADMIN_SECRET>` 重置本機資料庫（只會清空本機履歷/對話測試資料，**不會影響 Supabase 帳號**，不需要重新註冊）。
- Ollama 本地 AI 面試功能設定方式跟主 `README.md` 完全相同，沒有變動。
