# AI Career Coach（avatar_Huang_merge 分支）

AI 驅動的職涯輔助平台，提供 **AI 模擬面試**（含 3D 虛擬面試官／HeyGen 擬真面試官兩種模式）與 **AI 履歷評鑑** 功能。

- **前端**：Next.js 16 + TypeScript
- **後端**：Python FastAPI
- **登入/註冊**：Supabase Auth（JWT）
- **AI 面試對話**：Ollama 本地 LLM（llama-3-8b）／Gemini（可切換）
- **AI 模擬面試官**：3D 虛擬人（TalkingHead + Three.js + Azure TTS）或 HeyGen LiveAvatar 擬真影像
- **履歷評鑑／PDF・Word 上傳解析**：Google Gemini API

> **注意**：Vercel、Render、Neon（雲端資料庫）、Supabase、Azure、LiveAvatar 的正式帳號權限僅限專案負責人持有。
> 其他開發者請依照本文件在**本機**建立完整的獨立測試環境。

---

## 本分支的整合內容

本分支（`avatar_Huang_merge`）是 `Huang` 分支（登入系統重構）與 `avatar-local` 分支（3D／HeyGen 虛擬面試官、面試場次系統、AI 報告、履歷 PDF 解析、全站 UI 改版）的整合結果，並統一了兩者原本不一致的身份驗證方式。

1. **登入/註冊系統統一使用 Supabase Auth**（沿用 `Huang` 分支的做法，取代舊版自建 email+密碼系統）
   - 後端所有受保護端點一律透過驗證 Supabase 簽發的 JWT 取得使用者身份，**不再信任前端傳來的 `user_id` 字串**。
   - 新增「忘記密碼」功能（`/reset-password` 頁面）。
2. **`avatar-local` 帶來的新功能路由（`avatar.py`／`heygen.py`／`interview.py`／`resume_upload.py`）已全數改為 JWT 驗證**
   - 這些模組原本在 `avatar-local` 分支上是直接信任 request 裡的 `user_id` 欄位（沒有任何身份驗證），整合時已全部改成 `Depends(get_current_user)`，從 `Authorization: Bearer <token>` 解出已驗證的使用者，避免任何人猜到他人 ID 就能操作其資料。
   - 前端對應呼叫也已全部改為附上 Supabase session 的 `access_token`，不再依賴 `sessionStorage` 裡的 `user_id`。
3. **履歷上傳解析保留兩種實作**：
   - `POST /api/resume/parse`（原 `Huang` 分支）：支援 PDF／Word，後端先抽取純文字再交給 Gemini 整理成欄位，檔案本體即時丟棄不儲存。
   - `POST /api/resume/upload`（原 `avatar-local` 分支）：僅支援 PDF，直接把 PDF 位元組交給 Gemini 原生解析（對複雜排版可能效果更好）。
   - 兩者皆已改為 JWT 驗證，使用哪一個由前端頁面決定。
4. **資料庫本身沒有換**，仍是 Neon（生產）／SQLite（本地）。**注意：本次整合會清空正式環境資料庫重建 schema**（`users` 表拿掉密碼／驗證相關欄位、`id` 改為對應 Supabase UUID；新增 `interview_sessions` 表），既有測試資料不會被搬移。

---

## 技術架構

**前端**：Next.js 16（App Router）、React 19、Bootstrap、Three.js／TalkingHead
**後端**：FastAPI、SQLAlchemy
**資料庫**：本地 SQLite ／ 生產環境 Neon PostgreSQL
**AI／雲端服務**：Ollama 本地 LLM（面試對話，預設，可用 `USE_GEMINI_CHAT=1` 切成 Gemini）、Google Gemini（履歷解析、AI 報告、履歷評鑑）、Azure Speech（3D 模式語音合成）、LiveAvatar/HeyGen（擬真虛擬人）、Supabase Auth（登入/註冊）

```
使用者 (瀏覽器)
   │  文字／語音輸入
   ▼
Next.js 前端  ──►  FastAPI 後端（JWT 驗證）  ──►  Gemini（產生面試官回覆／報告／履歷解析）
   │                    │
   │                    └──►  Azure TTS（語音＋嘴型資料）
   │
   └── 3D 模式：TalkingHead 於瀏覽器渲染人物並同步嘴型
   └── 擬真模式：內嵌 LiveAvatar 即時影像串流
```

---

## 專案結構

```
後端（repo 根目錄）
├── Main.py            # FastAPI 主程式、JWT 驗證、對話、履歷、路由掛載
├── Model.py           # 資料表定義（User、ChatMessage、InterviewSession）
├── avatar.py          # Azure TTS 語音合成端點（提供 3D 模式音訊與 viseme）
├── heygen.py          # LiveAvatar 擬真虛擬人 embed 端點
├── interview.py       # 面試場次系統：開始／對話／結束報告／歷史紀錄
└── resume_upload.py   # 履歷 PDF 上傳與 Gemini 原生解析

前端（frontend/app/）
├── AuthPage/AuthPage.tsx    # 登入／註冊／忘記密碼（Supabase Auth）
├── reset-password/page.tsx # 忘記密碼重設頁
├── chat/
│   ├── page.tsx            # 面試室主頁：模式選擇 → 面試 → 報告
│   ├── Avatar3D.tsx        # 3D 虛擬面試官元件
│   ├── HeyGenAvatar.tsx    # 擬真面試官元件
│   ├── InputBox.tsx        # 文字＋語音輸入列
│   └── VoiceInputButton.tsx# 語音輸入按鈕
├── records/page.tsx        # 面試歷史紀錄與詳細報告
├── resume/                 # 履歷健檢與 PDF/Word 上傳
├── template.tsx             # 全域頁面轉場動畫
└── globals.css              # 視訊面試室主題樣式
```

---

## 本地開發環境建置

### 前置需求

| 工具 | 版本 | 說明 |
|---|---|---|
| Python | 3.12（建議） | 後端執行環境；3.14 部分套件相容性尚未完整 |
| Node.js | 18+ | 前端執行環境 |
| Git | 任意 | 版本控制 |
| Supabase 帳號 | 免費方案即可 | 登入/註冊功能用 |
| Azure Speech 帳號 | 免費方案即可 | 3D 模式語音合成用（選用） |
| LiveAvatar 帳號 | 免費沙盒即可 | 擬真面試官模式用（選用） |
| Ollama | 最新版 | AI 面試功能預設用的引擎（可用 `USE_GEMINI_CHAT=1` 改走 Gemini、跳過安裝） |

- Supabase 註冊：https://supabase.com
- Azure Speech：https://portal.azure.com（建立「語音服務」資源）
- LiveAvatar：https://app.liveavatar.com
- Ollama 下載：https://ollama.com

### 1. 取得專案
```bash
git clone https://github.com/Wei0309-lang/AI_Career_Coach.git
cd AI_Career_Coach
git checkout avatar_Huang_merge
```

### 2. 準備 Supabase 專案

到 Supabase Dashboard 設定：

1. **Authentication → URL Configuration → Redirect URLs**，加入 `http://localhost:3000/reset-password`（忘記密碼功能需要）
2. 到 **Settings → API** 頁面，記下 `Project URL` 與 `anon public key`，下一步會用到

### 3. 後端設定

```bash
# 建立並啟用虛擬環境（Windows PowerShell）
python -m venv venv
.\venv\Scripts\Activate.ps1

# 安裝套件
pip install -r requirements.txt
```

複製範本並填入實際金鑰（`.env` 切勿上傳至 git）：
```bash
Copy-Item .env.example .env
```

後端 `.env` 主要變數：

| 變數 | 是否必填 | 說明 |
|---|---|---|
| `GEMINI_API_KEY` | **必填** | 見下方「取得 Gemini API Key」 |
| `SUPABASE_URL` | **必填** | Step 2 記下的 Supabase Project URL |
| `ADMIN_SECRET` | 建議填 | 任意字串即可，用於 `/api/reset-db` |
| `MAX_RESUME_UPLOAD_MB` | 選填 | 履歷檔案大小上限（MB），不填預設 10 |
| `USE_GEMINI_CHAT` | 選填 | 面試對話與 AI 報告預設走本地 Ollama；設為 `1` 改走 Gemini，免安裝本地模型（履歷評鑑/解析一律用 Gemini，不受此開關影響） |
| `AZURE_SPEECH_KEY` / `AZURE_SPEECH_REGION` / `AZURE_SPEECH_VOICE` | 3D 模式必填 | Azure 語音服務金鑰、區域（如 `eastasia`）、音色 |
| `LIVEAVATAR_API_KEY` / `LIVEAVATAR_AVATAR_ID` / `LIVEAVATAR_CONTEXT_ID` | 擬真模式必填 | LiveAvatar 擬真面試官設定 |
| `LIVEAVATAR_SANDBOX` | 選填 | 設為 `1` 使用免費沙盒模式測試 |
| `ALLOWED_ORIGINS` | 必填 | CORS 允許來源，本地填 `http://localhost:3000` |

#### 取得 Gemini API Key

1. 前往 https://aistudio.google.com
2. 登入 Google 帳號
3. 點選左側「Get API Key」→「Create API Key」
4. 複製產生的金鑰，貼入 `.env` 的 `GEMINI_API_KEY=` 後方

免費方案即可使用，不需綁定信用卡。

### 4. 前端設定

```bash
cd frontend
npm install
Copy-Item .env.local.example .env.local
```

前端 `frontend/.env.local`：

| 變數 | 是否必填 | 說明 |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | 不需改 | 預設已指向 `http://localhost:8001` |
| `NEXT_PUBLIC_SUPABASE_URL` | **必填** | Step 2 記下的 Supabase Project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | **必填** | Step 2 記下的 anon public key |
| `NEXT_PUBLIC_AVATAR_MODE` | 選填 | 面試官模式：`3d`（自建）或 `heygen`（擬真） |
| `NEXT_PUBLIC_AVATAR_GLB_URL` | 選填 | 3D 模型路徑，例如 `/avatar-black.glb` |

`anon/public key` 設計上就是給前端公開使用的，可安全放在這裡；但 `.env`／`.env.local` 本身仍不可提交進 git（已在 `.gitignore` 排除）。

### 5. 啟動服務

開啟**兩個**終端機視窗：

**終端機 1 — 後端**（於專案根目錄、venv 啟用狀態）：
```bash
python -m uvicorn Main:app --reload --port 8001
```

**終端機 2 — 前端**（於 frontend 資料夾）：
```bash
npm run dev
```

兩者皆啟動後，瀏覽器開啟 `http://localhost:3000`。

### 6. 測試帳號註冊流程

信箱驗證完全由 Supabase 處理，不需要手動操作資料庫：

1. 在前端正常操作「註冊」，填入 Email 與密碼送出
2. 到收件信箱收驗證信（Supabase 預設寄出）
3. 點擊驗證連結後即可回到前端正常登入

### 7. Ollama 模型設定（AI 面試功能，預設必做）

> 此步驟影響 `/chat` 與「AI 模擬面試」（`/api/interview/*`）兩個對話功能，兩者預設都走本地 Ollama 模型。
> 若 `.env` 設定 `USE_GEMINI_CHAT=1` 可跳過本步驟，改用 Gemini。

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

## 使用流程

1. 註冊 / 登入 → 完成信箱驗證
2.（選用）於「履歷健檢」上傳履歷 PDF／Word 或手動填寫，供面試官出題參考
3. 進入「AI 模擬面試」，選擇 3D 或擬真模式、目標職位與應徵級別
4. 與虛擬面試官進行對話（可用文字或語音）
5. 結束面試，取得 AI 評估報告
6. 於「面試歷史紀錄」回顧歷次評分與逐字稿

---

## 功能測試對照表

| 功能 | 本地可用 | 前置條件 | 注意事項 |
|---|---|---|---|
| 註冊帳號 | ✅ | 已建立 Supabase 專案 | 驗證信由 Supabase 寄出 |
| 登入 | ✅ | 帳號已完成信箱驗證 | 無 |
| 忘記密碼 | ✅ | Redirect URLs 已設定 `/reset-password` | 見「準備 Supabase 專案」 |
| 履歷評鑑 | ✅ | 填入 `GEMINI_API_KEY` | 免費申請即可 |
| 履歷 PDF/Word 上傳解析 | ✅ | 填入 `GEMINI_API_KEY` | 檔案僅解析文字，不會被儲存 |
| AI 面試（/chat） | ✅ | 完成 Step 7 或設定 `USE_GEMINI_CHAT=1` | 需下載 4.6 GB 模型（若不用 Gemini） |
| AI 模擬面試（面試場次系統） | ✅ | 完成 Step 7 或設定 `USE_GEMINI_CHAT=1` | 對話與 AI 報告皆走同一顆 Ollama 模型；`GEMINI_API_KEY` 仍需要（履歷解析用） |
| 3D 虛擬面試官 | ✅ | 填入 `AZURE_SPEECH_*` | 需瀏覽器支援 WebGL |
| HeyGen 擬真面試官 | ✅ | 填入 `LIVEAVATAR_*` | 沙盒模式有時間限制 |
| 面試場次與 AI 報告 | ✅ | 填入 `GEMINI_API_KEY` | 無 |

---

## API 變更對照（相對 `master` 分支）

| 項目 | master 分支 | 本分支 |
|---|---|---|
| `POST /api/register`、`POST /api/login`、`GET /api/verify` | 有 | **已移除**，改由前端直接呼叫 Supabase SDK |
| `GET /api/resume/{user_id}` | 路徑帶 `user_id` | **改成 `GET /api/resume`**，身份從 `Authorization: Bearer <token>` 取得 |
| `POST /api/resume` | body 需帶 `user_id` | body **不需要 `user_id`**，身份從 JWT 取得 |
| `POST /chat` | body 需帶 `user_id` | body **不需要 `user_id`**，身份從 JWT 取得 |
| `POST /api/resume/parse` | 沒有 | **新增**，上傳 PDF/Word 履歷檔案，身份從 JWT 取得 |
| `POST /api/resume/upload` | 沒有 | **新增**，上傳 PDF 履歷檔案（Gemini 原生解析），身份從 JWT 取得 |
| `POST /avatar/*` | 沒有 | **新增**，Azure TTS 語音合成，身份從 JWT 取得 |
| `POST /heygen/*` | 沒有 | **新增**，LiveAvatar embed session，身份從 JWT 取得 |
| `POST /interview/*` | 沒有 | **新增**，面試場次開始／對話／結束／歷史紀錄，身份從 JWT 取得 |

呼叫任何受保護端點時，前端都要在 header 帶上 `Authorization: Bearer <session.access_token>`（`session` 來自 `supabase.auth.getSession()`）。

---

## 常見問題

**Q：`pip install` 失敗或出現找不到套件的錯誤**

確認 Python 版本為 3.10 以上，且虛擬環境已啟動——提示字元最前面應出現 `(venv)`。

**Q：後端啟動時出現 `GEMINI_API_KEY` 相關錯誤**

`.env` 檔案中的 `GEMINI_API_KEY` 未填入，或金鑰格式錯誤。

**Q：`/api/resume`、`/chat`、`/interview/*` 回傳 401**

多半是前端沒帶到 `Authorization` header，或後端 `SUPABASE_URL` 沒填對。確認：
1. 瀏覽器 Console 執行 `Object.keys(localStorage)`，應該要看到 `sb-<project-ref>-auth-token`
2. `.env` 的 `SUPABASE_URL` 跟 `frontend/.env.local` 的 `NEXT_PUBLIC_SUPABASE_URL` 是同一個值
3. 修改 `.env`／`.env.local` 後**務必完全重啟**對應的終端機（`Ctrl+C` 再重新執行），單純熱重載不會重新讀取環境變數

**Q：`/api/resume` 回傳 500，錯誤訊息提到 `NOT NULL constraint failed`；或「開始面試」按下去瀏覽器顯示 CORS 錯誤，但後端 log 其實是 `no column named session_id`**

兩者都代表本機 `app.db` 是合併前的舊版 schema（帶有 `is_verified`、`password_hash` 等舊欄位，或缺少 `chat_messages.session_id`）。`create_all` 只會新增不存在的資料表，不會幫舊表補欄位，所以要手動重置。呼叫以下網址即可（只會清空本機測試資料與履歷/面試紀錄，**不會影響 Supabase 帳號**，不需要重新註冊,但要重新登入）：

```
http://localhost:8001/api/reset-db?secret=<你的 ADMIN_SECRET>
```

> 補充：瀏覽器主控台把這類未捕捉的後端例外顯示成「CORS policy 封鎖」是正常現象——未捕捉的例外會跳過 CORS middleware，回應沒有 CORS header，瀏覽器就會誤判成 CORS 問題。遇到類似訊息時，先去看後端終端機的實際 log 找真正的例外。

**Q：`/chat` 或「AI 模擬面試」回傳 500 錯誤**

可能原因有二：
1. Ollama 服務未在背景執行——開啟 Ollama 應用程式後再試（或設定 `USE_GEMINI_CHAT=1` 改用 Gemini）
2. `my-career-coach` 模型尚未建立——重新執行 Step 7-2

**Q：3D 虛擬面試官沒有聲音／嘴型不同步**

確認 `AZURE_SPEECH_KEY`／`AZURE_SPEECH_REGION` 已正確填入，且該 Azure 資源額度未用盡。

---

## 備註

- 3D 模式使用之虛擬人模型放置於 `frontend/public/`（`.glb` 格式）。
- 擬真模式的沙盒（Sandbox）session 有時間限制，屬服務端正常行為；正式展示需使用付費額度。
- 本地開發使用 SQLite（`app.db`）；若變更資料表結構，需刪除 `app.db` 後重啟後端以重建。
