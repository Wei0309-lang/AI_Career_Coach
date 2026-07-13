# AI 職涯導師 — 智慧模擬面試平台

> 本文件說明本人於團隊畢業專題「AI Career Coach」中負責之模組。
> 對應分支：`avatar-local`

一套讓求職者與 **AI 虛擬面試官**進行即時對話練習的平台。系統提供兩種面試官呈現模式——自建的 **3D 虛擬人**與商用服務串接的**擬真真人影像**——並在面試結束後產出 **AI 評估報告**，協助使用者複盤與追蹤進步。

---

## 一、負責功能總覽

| 模組 | 說明 |
|------|------|
| **3D 虛擬面試官** | 以 TalkingHead + Three.js 於瀏覽器即時渲染 3D 人物，串接 Azure 語音合成（TTS），並透過 viseme（嘴型音素）資料驅動嘴型與語音同步。 |
| **擬真面試官模式** | 串接 LiveAvatar（HeyGen）即時虛擬人，提供照片級真人影像的面試體驗。與 3D 模式可透過環境變數一鍵切換。 |
| **面試場次系統** | 使用者可選擇目標職位與應徵級別，面試官依此動態調整提問方向與評估標準；每場面試為獨立場次，對話記憶限定於場次內。 |
| **AI 評估報告** | 面試結束後，將完整對話交由 Gemini 分析，產出總分、三維度評分（技術深度／溝通表達／問題解決）、表現亮點與改進建議。 |
| **面試歷史紀錄** | 保存每場面試的評分與逐字稿，可點擊展開完整報告，追蹤練習軌跡。 |
| **履歷 PDF 解析** | 上傳履歷 PDF，由 Gemini 解析內容並自動填入表單；面試官會依履歷內容提出個人化問題。 |
| **語音／文字輸入** | 支援以 Web Speech API 語音輸入（繁體中文辨識），可與文字輸入自由混用。 |
| **整體 UI** | 以「視訊面試室」為主題設計的深色介面，含 ON AIR 錄影提示、面試官名牌、全站頁面轉場動畫。 |

---

## 二、技術架構

**前端**：Next.js 16（App Router）、React 19、Bootstrap、Three.js／TalkingHead
**後端**：FastAPI、SQLAlchemy
**資料庫**：本地 SQLite ／ 生產環境 Neon PostgreSQL
**AI／雲端服務**：Google Gemini（對話與解析）、Azure Speech（語音合成）、LiveAvatar/HeyGen（擬真虛擬人）

```
使用者 (瀏覽器)
   │  文字／語音輸入
   ▼
Next.js 前端  ──►  FastAPI 後端  ──►  Gemini（產生面試官回覆／報告）
   │                    │
   │                    └──►  Azure TTS（語音＋嘴型資料）
   │
   └── 3D 模式：TalkingHead 於瀏覽器渲染人物並同步嘴型
   └── 擬真模式：內嵌 LiveAvatar 即時影像串流
```

---

## 三、專案結構（本人負責之主要檔案）

```
後端（repo 根目錄）
├── Main.py            # FastAPI 主程式、登入註冊、對話、履歷、路由掛載
├── Model.py           # 資料表定義（User、ChatMessage、InterviewSession）
├── avatar.py          # Azure TTS 語音合成端點（提供 3D 模式音訊與 viseme）
├── heygen.py          # LiveAvatar 擬真虛擬人 embed 端點
├── interview.py       # 面試場次系統：開始／對話／結束報告／歷史紀錄
└── resume_upload.py   # 履歷 PDF 上傳與 Gemini 解析

前端（frontend/app/）
├── chat/
│   ├── page.tsx            # 面試室主頁：模式選擇 → 面試 → 報告
│   ├── Avatar3D.tsx        # 3D 虛擬面試官元件
│   ├── HeyGenAvatar.tsx    # 擬真面試官元件
│   ├── InputBox.tsx        # 文字＋語音輸入列
│   └── VoiceInputButton.tsx# 語音輸入按鈕
├── records/page.tsx        # 面試歷史紀錄與詳細報告
├── resume/                 # 履歷健檢與 PDF 上傳
├── template.tsx            # 全域頁面轉場動畫
└── globals.css             # 視訊面試室主題樣式
```

---

## 四、安裝與啟動

### 環境需求
- Python 3.12（建議；3.14 部分套件相容性尚未完整）
- Node.js 18 以上

### 1. 取得專案
```bash
git clone -b avatar-local https://github.com/Wei0309-lang/AI_Career_Coach.git
cd AI_Career_Coach
```

### 2. 後端環境
```bash
# 建立並啟用虛擬環境（Windows PowerShell）
python -m venv venv
.\venv\Scripts\Activate.ps1

# 安裝套件
pip install -r requirements.txt
pip install azure-cognitiveservices-speech pyjwt   # 額外依賴
```

### 3. 設定環境變數
複製範本並填入實際金鑰（`.env` 切勿上傳至 git）：
```bash
Copy-Item .env.example .env            # 後端
Copy-Item frontend\.env.local.example frontend\.env.local   # 前端
```

後端 `.env` 主要變數：

| 變數 | 用途 |
|------|------|
| `GEMINI_API_KEY` | Gemini 金鑰（對話、報告、履歷解析） |
| `GEMINI_MODEL` | 模型名稱，建議 `gemini-2.5-flash-lite`（較不易觸發流量限制） |
| `USE_GEMINI_CHAT` | 設為 `1` 時本地以 Gemini 取代 Ollama，免安裝本地模型 |
| `AZURE_SPEECH_KEY` / `AZURE_SPEECH_REGION` | Azure 語音服務（3D 模式 TTS），region 例如 `eastasia` |
| `AZURE_SPEECH_VOICE` | 語音音色，例如 `zh-TW-HsiaoChenNeural` |
| `LIVEAVATAR_API_KEY` / `LIVEAVATAR_AVATAR_ID` / `LIVEAVATAR_CONTEXT_ID` | 擬真面試官設定 |
| `LIVEAVATAR_SANDBOX` | 設為 `1` 使用免費沙盒模式測試 |
| `ALLOWED_ORIGINS` | CORS 允許來源，本地填 `http://localhost:3000,http://127.0.0.1:3000` |

前端 `frontend/.env.local`：

| 變數 | 用途 |
|------|------|
| `NEXT_PUBLIC_API_URL` | 後端位址，本地為 `http://localhost:8001` |
| `NEXT_PUBLIC_AVATAR_MODE` | 面試官模式：`3d`（自建）或 `heygen`（擬真） |
| `NEXT_PUBLIC_AVATAR_GLB_URL` | 3D 模型路徑，例如 `/avatar-black.glb` |

### 4. 前端環境
```bash
cd frontend
npm install
```

### 5. 啟動（需同時運行前後端）

**終端機 1 — 後端**（於專案根目錄、venv 啟用狀態）：
```bash
python -m uvicorn Main:app --reload --port 8001
```

**終端機 2 — 前端**（於 frontend 資料夾）：
```bash
npm run dev
```

兩者皆啟動後，瀏覽器開啟 `http://localhost:3000`。

> **首次使用**：註冊後需完成信箱驗證。本地若未設定寄信金鑰，驗證連結會直接印在後端終端機的 log（`🔗 驗證連結: ...`），複製至瀏覽器開啟即可完成驗證。

---

## 五、使用流程

1. 註冊 / 登入 → 完成信箱驗證
2.（選用）於「履歷健檢」上傳履歷 PDF 或手動填寫，供面試官出題參考
3. 進入「AI 模擬面試」，選擇目標職位與應徵級別
4. 與虛擬面試官進行對話（可用文字或語音）
5. 結束面試，取得 AI 評估報告
6. 於「面試歷史紀錄」回顧歷次評分與逐字稿

---

## 六、備註

- 3D 模式使用之虛擬人模型放置於 `frontend/public/`（`.glb` 格式）。
- 擬真模式的沙盒（Sandbox）session 有時間限制，屬服務端正常行為；正式展示需使用付費額度。
- 本地開發使用 SQLite（`app.db`）；若變更資料表結構，需刪除 `app.db` 後重啟後端以重建。
