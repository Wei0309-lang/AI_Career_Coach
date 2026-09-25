# 系統架構與資料庫設計

本文件依照目前程式碼（`master` 分支）繪製，圖表使用 [Mermaid](https://mermaid.js.org/) 語法，GitHub 會直接渲染成圖。
需要放進專題報告時，可將各段 ` ```mermaid ` 區塊內容貼到 [mermaid.live](https://mermaid.live) 匯出 PNG / SVG。

- [1. 系統架構圖（部署與外部服務）](#1-系統架構圖部署與外部服務)
- [2. 後端模組圖](#2-後端模組圖)
- [3. ERD（資料庫實體關係圖）](#3-erd資料庫實體關係圖)
- [4. 面試場次狀態圖](#4-面試場次狀態圖)
- [5. 循序圖：登入與 API 身份驗證](#5-循序圖登入與-api-身份驗證)
- [6. 循序圖：模擬面試完整流程](#6-循序圖模擬面試完整流程)
- [7. 循序圖：履歷上傳解析與 AI 健檢](#7-循序圖履歷上傳解析與-ai-健檢)
- [8. API 一覽](#8-api-一覽)

---

## 1. 系統架構圖（部署與外部服務）

```mermaid
flowchart LR
    user(["使用者<br/>(Chrome / Edge)"])

    subgraph browser["瀏覽器"]
        fe["Next.js 16 前端<br/>React 19 + Bootstrap"]
        speech["Web Speech API<br/>語音輸入 (zh-TW)"]
        th["TalkingHead + three.js<br/>3D 虛擬面試官"]
    end

    subgraph vercel["Vercel"]
        static["前端網站<br/>cguimgraduatepj.me"]
    end

    subgraph render["Render"]
        api["FastAPI 後端<br/>api.cguimgraduatepj.me"]
    end

    subgraph supabase["Supabase"]
        sbauth["Auth<br/>帳號 / 密碼 / 驗證信 / 重設密碼"]
        jwks["JWKS 公鑰端點<br/>(ES256)"]
    end

    neon[("Neon PostgreSQL<br/>users / interview_sessions /<br/>chat_messages")]
    gemini["Google Gemini API<br/>gemini-2.5-flash"]
    ollama["Ollama（僅本機開發）<br/>Llama-3-8B my-career-coach"]
    azure["Azure Speech<br/>TTS + 嘴型 viseme"]
    heygen["HeyGen LiveAvatar<br/>擬真面試官（選用）"]
    cdn["jsDelivr CDN<br/>three.js / TalkingHead"]

    user --> fe
    static -- "載入網頁" --> fe
    fe --> speech
    fe --> th
    cdn -- "importmap 載入模組" --> th
    fe -- "登入 / 註冊 / 重設密碼<br/>(supabase-js)" --> sbauth
    fe -- "REST API<br/>Authorization: Bearer JWT" --> api
    api -- "取得公鑰驗證 JWT" --> jwks
    api -- "SQLAlchemy" --> neon
    api -- "履歷解析 / 健檢 / 面試對話 / 報告" --> gemini
    api -. "USE_GEMINI_CHAT=0 時<br/>面試改用本地模型" .-> ollama
    api -- "文字轉語音" --> azure
    api -- "建立 embed session" --> heygen
    fe -. "AVATAR_MODE=heygen 時<br/>嵌入 iframe" .-> heygen
```

**說明**

| 元件 | 角色 | 設定位置 |
|---|---|---|
| Vercel | 前端（Next.js）部署，`master` 推送後自動部署；其他分支產生 Preview | `NEXT_PUBLIC_*` 環境變數 |
| Render | 後端（FastAPI / uvicorn）部署，`master` 推送後自動部署 | Render Environment（`render.yaml` 僅供參考，服務未啟用 Blueprint 同步） |
| Supabase | **只負責帳號**（Auth）；後端不存密碼，只用 JWKS 公鑰驗證前端帶來的 JWT | `SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_*` |
| Neon | 應用資料（履歷、面試場次、對話）；本機開發改用 SQLite（`app.db`） | `DATABASE_URL` |
| Gemini | 履歷解析、履歷健檢；正式環境（`USE_GEMINI_CHAT=1`）也負責面試對話與報告 | `GEMINI_API_KEY` / `GEMINI_MODEL` |
| Ollama | 本機開發時的面試模型（`USE_GEMINI_CHAT=0`），Render 上沒有安裝 | `OLLAMA_HOST` / `OLLAMA_MODEL`、`Modelfile` |
| Azure Speech | 面試官語音與嘴型時間軸（區域 `southeastasia`） | `AZURE_SPEECH_*` |
| HeyGen | 擬真面試官模式（`NEXT_PUBLIC_AVATAR_MODE=heygen`），對話由 HeyGen 雲端處理，不經過面試場次系統 | `LIVEAVATAR_*` |

---

## 2. 後端模組圖

```mermaid
flowchart TB
    subgraph fastapi["FastAPI 應用 (Main.py)"]
        direction TB
        cors["CORSMiddleware<br/>只放行本專案網域"]
        main["Main.py<br/>/api/resume*、/api/reset-db、/chat(舊版)"]
        interview["interview.py<br/>/api/interview/*<br/>場次、對話、報告 schema"]
        avatar["avatar.py<br/>/avatar/tts"]
        heygenr["heygen.py<br/>/heygen/embed"]
    end

    auth["auth.py<br/>JWT 驗證 + get-or-create 使用者"]
    rl["rate_limit.py<br/>每位使用者限流 (429)"]
    utils["resume_utils.py<br/>AI 回傳值攤平成文字"]
    model["Model.py<br/>SQLAlchemy 資料表"]
    database["Database.py<br/>engine / SessionLocal"]

    cors --> main & interview & avatar & heygenr
    main --> rl
    interview --> rl
    avatar --> rl
    heygenr --> rl
    rl --> auth
    main -- "讀取類端點" --> auth
    interview -- "history / active / detail" --> auth
    main --> utils
    interview --> utils
    auth --> model
    main --> model
    interview --> model
    model --> database
```

- 會消耗 AI / 語音 / HeyGen 額度的 POST 端點都經過 `rate_limit.rate_limited()`，它內部再呼叫 `auth.get_current_user`；只讀取資料的端點直接用 `get_current_user`。
- `tests/test_security.py` 會檢查每個花額度的端點都有掛限流，之後新增端點若漏掛會被測試抓到。

---

## 3. ERD（資料庫實體關係圖）

```mermaid
erDiagram
    SUPABASE_AUTH_USERS ||..|| users : "id = Supabase 使用者 id"
    users ||..o{ interview_sessions : "user_id"
    users ||..o{ chat_messages : "user_id"
    interview_sessions |o..o{ chat_messages : "session_id"

    SUPABASE_AUTH_USERS {
        uuid id PK "Supabase Auth 管理(外部服務)"
        string email "登入帳號"
        string encrypted_password "密碼雜湊，後端看不到"
    }

    users {
        string id PK "= Supabase 使用者 id(JWT 的 sub)"
        string email UK "Supabase email 的副本，可為 NULL"
        string full_name "姓名"
        string summary "個人簡介"
        string skills "專業技能"
        string experience "工作 / 專案經歷"
    }

    interview_sessions {
        string id PK "UUID"
        string user_id "索引，對應 users.id"
        string position "前端 / 後端 / 資安 / 全端工程師"
        string level "實習生 / 新鮮人 / 資深工程師"
        string status "active / finished / abandoned"
        text report_json "AI 評估報告(JSON)，結束後才有"
        datetime created_at "UTC"
        datetime finished_at "UTC，可為 NULL"
    }

    chat_messages {
        string id PK "UUID"
        string user_id "索引，對應 users.id"
        string session_id "索引，對應 interview_sessions.id；舊版 /chat 為 NULL"
        string role "user / assistant"
        string content "訊息內容"
        datetime created_at "UTC"
    }
```

**設計說明（撰寫報告時可引用）**

- **帳號與應用資料分離**：密碼、驗證信、重設密碼全部交給 Supabase Auth；`users` 只存履歷欄位，主鍵直接使用 Supabase 的使用者 id（JWT 的 `sub`）。使用者第一次呼叫受保護 API 時，由 `auth.get_current_user` 自動建立資料列（get-or-create）。
- **關聯為邏輯關聯（圖中虛線）**：程式以 `user_id`、`session_id` 欄位關聯並建立索引，但資料庫層沒有 FOREIGN KEY 約束；刪除 Supabase 帳號時，Neon 中的資料不會連帶刪除。
- **同 email 重新註冊**：Supabase 保證同一時間一個 email 只屬於一個帳號，若本地有「其他 id」仍佔用該 email（已刪除的舊帳號），會先把舊資料列的 email 清空再建立新帳號；舊履歷與面試紀錄保留，但不會轉給新帳號。
- **報告以 JSON 字串存在 `report_json`**：讀寫時都經過 `interview.InterviewReport`（Pydantic）補齊欄位與校正分數範圍，前端永遠拿到完整結構。
- **時間一律存 UTC**，回傳給前端前轉成台灣時間（UTC+8）。
- **Schema 管理**：啟動時 `Base.metadata.create_all()` 只會新增不存在的資料表；既有資料表要改欄位時，需在 Render 暫時設定 `ALLOW_DB_RESET=1` 並呼叫 `POST /api/reset-db`（會清空資料，見 README 常見問題）。

---

## 4. 面試場次狀態圖

```mermaid
stateDiagram-v2
    [*] --> active : POST /api/interview/start<br/>建立場次並產生開場白
    active --> active : POST /api/interview/chat<br/>每輪對話
    active --> finished : POST /api/interview/finish<br/>產生並儲存 AI 報告
    active --> abandoned : 同一使用者開始新的面試<br/>(未結束的舊場次)
    finished --> finished : 再次 finish<br/>直接回傳已存報告，不重新呼叫 AI
    finished --> [*]
    abandoned --> [*]

    note right of active
        重新整理頁面後，前端以
        GET /api/interview/active
        取回對話紀錄接續面試
    end note
```

- 同一位使用者同時最多只有一場 `active` 場次。
- `abandoned` 的場次不能再對話或產生報告（回 400），也不會出現在歷史紀錄。
- 報告產生失敗（AI 連線錯誤或格式錯誤）時，場次維持 `active`，使用者可以再按一次「結束面試」。

---

## 5. 循序圖：登入與 API 身份驗證

```mermaid
sequenceDiagram
    autonumber
    actor U as 使用者
    participant FE as 前端 (Next.js)
    participant SA as Supabase Auth
    participant BE as 後端 (FastAPI)
    participant DB as Neon

    U->>FE: 輸入 Email / 密碼
    FE->>SA: signInWithPassword()
    SA-->>FE: session（access_token = ES256 JWT）
    Note over FE: supabase-js 自動保存與更新 session

    U->>FE: 進入面試 / 履歷 / 紀錄頁
    FE->>FE: AuthGuard：沒有 session 就導回首頁
    FE->>BE: API 請求 + Authorization: Bearer JWT
    BE->>SA: 取得 JWKS 公鑰（PyJWKClient，有快取）
    BE->>BE: 驗證簽章、audience=authenticated、取出 sub / email
    alt 憑證缺少或無效
        BE-->>FE: 401
    else 驗證成功
        BE->>DB: 依 sub 查詢 users
        opt 第一次登入
            BE->>DB: 讓出被舊帳號佔用的 email → 建立 users 資料列
        end
        BE->>BE: rate_limit 檢查（花額度的端點）
        BE-->>FE: 200 回應資料
    end
```

---

## 6. 循序圖：模擬面試完整流程

```mermaid
sequenceDiagram
    autonumber
    actor U as 使用者
    participant FE as 前端 /chat
    participant BE as 後端 interview.py
    participant DB as Neon
    participant AI as Gemini（本機：Ollama）
    participant TTS as Azure Speech

    FE->>BE: GET /api/interview/active
    BE-->>FE: 有未結束場次 → 顯示「繼續這場面試」

    U->>FE: 選擇職位與級別，開始面試
    FE->>BE: POST /api/interview/start
    BE->>DB: 舊的 active 場次 → abandoned；建立新場次
    BE->>AI: 依履歷 + 職位 + 級別產生開場白
    AI-->>BE: 開場白
    BE->>DB: 儲存開場白
    BE-->>FE: session_id + 開場白

    loop 每一輪問答
        FE->>BE: POST /avatar/tts（面試官這句話）
        BE->>TTS: 合成語音
        TTS-->>BE: mp3 + viseme 嘴型時間軸
        BE-->>FE: audio_base64 + visemes
        FE->>FE: 3D 面試官播放語音並同步嘴型
        U->>FE: 打字或語音輸入回答（回覆中不能送出）
        FE->>BE: POST /api/interview/chat
        BE->>DB: 取最近 20 則對話、儲存使用者回答
        BE->>AI: system prompt（履歷 + 職位 + 級別）+ 對話
        AI-->>BE: 面試官追問
        BE->>DB: 儲存面試官回覆
        BE-->>FE: 面試官回覆
    end

    U->>FE: 結束面試並取得報告
    FE->>BE: POST /api/interview/finish
    BE->>DB: 讀取完整逐字稿
    BE->>AI: 報告 system prompt + JSON 模式（格式錯誤自動重試一次）
    AI-->>BE: 報告 JSON
    BE->>BE: InterviewReport 驗證：補齊欄位、分數限制在 0–10 / 0–100
    BE->>DB: status = finished，儲存 report_json
    BE-->>FE: 報告（總分、三個維度、優點、建議、總評）
    U->>FE: 到「面試歷史紀錄」查看
    FE->>BE: GET /api/interview/history、/detail/{id}
```

---

## 7. 循序圖：履歷上傳解析與 AI 健檢

```mermaid
sequenceDiagram
    autonumber
    actor U as 使用者
    participant FE as 前端 /resume
    participant BE as 後端 Main.py
    participant AI as Gemini
    participant DB as Neon

    FE->>BE: GET /api/resume
    BE-->>FE: 既有履歷四個欄位
    U->>FE: 上傳 PDF / Word（上限 10MB）
    FE->>BE: POST /api/resume/parse（multipart）
    BE->>BE: 檢查副檔名與大小
    BE->>BE: 抽取文字（PDF：pypdf；Word：內文、表格、文字方塊、頁首頁尾）
    alt 抽不到文字（掃描檔）或檔案毀損
        BE-->>FE: 400 錯誤訊息
    else 有文字
        BE->>AI: 整理成 fullName / summary / skills / experience（JSON 模式）
        AI-->>BE: JSON
        BE->>BE: 攤平陣列 / 物件成純文字
        BE-->>FE: 四個欄位（只回填表單，尚未存檔）
    end
    U->>FE: 確認或修改後送出
    FE->>BE: POST /api/resume
    BE->>DB: 儲存履歷（面試官之後會引用）
    BE->>AI: 產生 3–5 點修改建議
    AI-->>BE: 建議文字
    BE-->>FE: 建議（AI 失敗時仍會存檔，並提示稍後再試）
```

---

## 8. API 一覽

| 方法 | 路徑 | 說明 | 身份驗證 | 限流 |
|---|---|---|---|---|
| GET | `/` | 健康檢查 | — | — |
| GET | `/api/resume` | 讀取目前使用者的履歷 | JWT | — |
| POST | `/api/resume` | 儲存履歷並取得 AI 健檢建議 | JWT | 10 次 / 10 分鐘 |
| POST | `/api/resume/parse` | 上傳 PDF / Word，AI 解析成履歷欄位 | JWT | 10 次 / 10 分鐘 |
| POST | `/api/interview/start` | 開始面試（職位、級別），回傳開場白 | JWT | 10 次 / 10 分鐘 |
| POST | `/api/interview/chat` | 場次內對話 | JWT | 20 次 / 分鐘 |
| POST | `/api/interview/finish` | 結束面試並產生報告 | JWT | 10 次 / 10 分鐘 |
| GET | `/api/interview/active` | 取得未結束的場次（接續面試） | JWT | — |
| GET | `/api/interview/history` | 已完成的面試列表 | JWT | — |
| GET | `/api/interview/detail/{id}` | 單場報告與逐字稿 | JWT | — |
| POST | `/avatar/tts` | Azure 文字轉語音 + 嘴型時間軸 | JWT | 40 次 / 分鐘 |
| POST | `/heygen/embed` | 建立 HeyGen 擬真面試官 iframe | JWT | 5 次 / 小時 |
| POST | `/chat` | 舊版不分場次的對話（前端已不使用） | JWT | 20 次 / 分鐘 |
| POST | `/api/reset-db` | 清空並重建資料表（需 `ALLOW_DB_RESET=1` 與 `X-Admin-Secret`） | Admin secret | — |

互動式 API 文件：啟動後端後開啟 `http://localhost:8001/docs`（FastAPI 自動產生）。
