"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Container from "react-bootstrap/Container";
import AuthGuard from "../components/AuthGuard";
import { supabase } from "../lib/supabaseClient";

const MAX_UPLOAD_SIZE_MB = 10;

function ResumePageContent() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [suggestion, setSuggestion] = useState<string>("");

  // 檔案上傳解析狀態
  const [parsing, setParsing] = useState(false);
  const [uploadNotice, setUploadNotice] = useState("");
  const [uploadError, setUploadError] = useState("");
  const pdfInputRef = useRef<HTMLInputElement>(null);
  const wordInputRef = useRef<HTMLInputElement>(null);

  // 表單資料狀態
  const emptyResume = { fullName: "", summary: "", skills: "", experience: "" };
  const [formData, setFormData] = useState(emptyResume);
  // 最後一次已知「已儲存」的內容，用來判斷目前表單是否有未送出的變更
  const [savedData, setSavedData] = useState(emptyResume);
  const isDirty = JSON.stringify(formData) !== JSON.stringify(savedData);

  // 進入頁面時去後端撈取歷史履歷資料
  useEffect(() => {
    fetchExistingResume();
  }, []);

  // 離開分頁（關閉/重新整理/跳轉外部網址）時，若有未儲存的變更則提醒使用者
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
      }
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isDirty]);

  // 向後端 API 撈取歷史資料的函式
  const fetchExistingResume = async () => {
    try {
      const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      const response = await fetch(`${BACKEND_URL}/api/resume`, {
        headers: { "Authorization": `Bearer ${session.access_token}` },
      });

      if (response.ok) {
        const data = await response.json();
        // 將撈到的舊資料直接覆蓋到表單狀態中，讓輸入框直接呈現，並設為目前的「已儲存」基準
        const resume = {
          fullName: data.fullName,
          summary: data.summary,
          skills: data.skills,
          experience: data.experience,
        };
        setFormData(resume);
        setSavedData(resume);
      }
    } catch (err) {
      console.error("❌ 無法載入歷史履歷資料:", err);
    }
  };

  // 判斷目前表單是否已有內容（不論是已儲存還是尚未送出），上傳新檔案前用來決定要不要跳確認
  const hasExistingContent = () =>
    Object.values(formData).some((v) => v.trim() !== "");

  // 上傳 PDF/Word 履歷檔案，解析後自動帶入表單欄位
  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ""; // 允許重複選同一個檔案時仍能觸發 onChange
    if (!file) return;

    setUploadNotice("");
    setUploadError("");

    // 已上傳過履歷、或已解析但還沒送出：上傳新檔案前先提醒會覆蓋目前內容
    if (hasExistingContent()) {
      const confirmMessage = isDirty
        ? "目前表單有尚未送出的內容，上傳新檔案將會覆蓋，確定要繼續嗎？"
        : "目前已有履歷資料，上傳新檔案將會覆蓋，確定要繼續嗎？";
      if (!window.confirm(confirmMessage)) {
        return;
      }
    }

    if (file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
      setUploadError(`檔案大小超過 ${MAX_UPLOAD_SIZE_MB}MB 上限`);
      return;
    }

    setParsing(true);

    try {
      const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
      const { data: { session } } = await supabase.auth.getSession();

      if (!session) {
        throw new Error("尚未登入");
      }

      const body = new FormData();
      body.append("file", file);

      const response = await fetch(`${BACKEND_URL}/api/resume/parse`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${session.access_token}` },
        body,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "檔案解析失敗");
      }

      setFormData({
        fullName: data.fullName,
        summary: data.summary,
        skills: data.skills,
        experience: data.experience,
      });
      setUploadNotice("已將內容填入表格，確認無誤後請送出");
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "檔案解析失敗");
    } finally {
      setParsing(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setSuggestion("");

    try {
      const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
      const { data: { session } } = await supabase.auth.getSession();

      if (!session) {
        throw new Error("尚未登入");
      }

      const response = await fetch(`${BACKEND_URL}/api/resume`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session.access_token}`,
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        throw new Error("伺服器錯誤");
      }
      const data = await response.json();
      setSuggestion(data.suggestion);
      setSavedData(formData); // 送出成功，目前內容成為新的「已儲存」基準
      setUploadNotice("");
      setUploadError("");
    } catch (err) {
      setSuggestion("❌ 儲存失敗或 AI 健檢服務暫時無法使用，請檢查連線。");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="studio-bg py-5">
      <Container style={{ maxWidth: "860px" }}>
        <div className="studio-panel p-4 p-md-5">

          <div className="d-flex justify-content-between align-items-start mb-4">
            <div>
              <span className="studio-eyebrow">Resume Check</span>
              <h2 className="studio-title fs-3 mb-0">完善您的個人履歷</h2>
            </div>
            <button
              onClick={() => {
                if (isDirty && !window.confirm("目前有尚未送出的變更，離開後將會遺失，確定要離開嗎？")) {
                  return;
                }
                router.push("/");
              }}
              className="btn btn-studio-ghost btn-sm px-3"
            >
              返回首頁
            </button>
          </div>

          <p className="studio-dim small mb-4">
            此頁面已串接您的個人檔案。您可以隨時查看、調整或更新您的經歷，AI 面試官將即時採用最新內容！
            {isDirty && <span className="badge text-bg-warning ms-2">尚未儲存</span>}
          </p>

          <div
            className="mb-4 p-3 rounded-3"
            style={{ background: "rgba(255,255,255,.04)", border: "1px solid var(--studio-line)" }}
          >
            <p className="small mb-2" style={{ color: "var(--studio-text)", fontWeight: 700 }}>
              📄 上傳既有履歷檔案，自動帶入以下欄位
            </p>
            <p className="studio-dim small mb-3">支援 PDF、Word（.docx），檔案大小上限 {MAX_UPLOAD_SIZE_MB}MB</p>

            <input
              ref={pdfInputRef}
              type="file"
              accept=".pdf,application/pdf"
              className="d-none"
              onChange={handleFileSelected}
            />
            <input
              ref={wordInputRef}
              type="file"
              accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              className="d-none"
              onChange={handleFileSelected}
            />

            <button
              type="button"
              className="btn btn-studio-ghost btn-sm me-2"
              disabled={parsing}
              onClick={() => pdfInputRef.current?.click()}
            >
              上傳 PDF
            </button>
            <button
              type="button"
              className="btn btn-studio-ghost btn-sm"
              disabled={parsing}
              onClick={() => wordInputRef.current?.click()}
            >
              上傳 Word
            </button>

            {parsing && <p className="studio-dim small mt-2 mb-0">解析中，請稍候...</p>}
            {uploadNotice && (
              <p className="small mt-2 mb-0" style={{ color: "var(--studio-accent-2)" }}>✅ {uploadNotice}</p>
            )}
            {uploadError && (
              <p className="small mt-2 mb-0" style={{ color: "var(--studio-rec)" }}>❌ {uploadError}</p>
            )}
          </div>

          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label className="form-label small studio-dim">1. 姓名 (Full Name)</label>
              <input
                type="text"
                className="form-control studio-input"
                placeholder="請輸入您的真實姓名或暱稱"
                value={formData.fullName}
                onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
                required
              />
            </div>

            <div className="mb-3">
              <label className="form-label small studio-dim">2. 個人簡介 (Summary)</label>
              <textarea
                className="form-control studio-input"
                rows={3}
                placeholder="用 3-5 句話簡短介紹您自己、您的熱情以及職涯目標。"
                value={formData.summary}
                onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
                required
              ></textarea>
            </div>

            <div className="mb-3">
              <label className="form-label small studio-dim">3. 專業技能 (Skills)</label>
              <textarea
                className="form-control studio-input"
                rows={3}
                placeholder="列出您的硬實力與軟實力（例如：Python, React, 專案管理, 資料庫設計...）"
                value={formData.skills}
                onChange={(e) => setFormData({ ...formData, skills: e.target.value })}
                required
              ></textarea>
            </div>

            <div className="mb-4">
              <label className="form-label small studio-dim">4. 工作/專案經歷 (Experience)</label>
              <textarea
                className="form-control studio-input"
                rows={5}
                placeholder="請描述您過去的職位、參與過的專案，以及達成的具體成就。"
                value={formData.experience}
                onChange={(e) => setFormData({ ...formData, experience: e.target.value })}
                required
              ></textarea>
            </div>

            <button type="submit" className="btn btn-studio w-100" disabled={loading}>
              {loading ? "儲存中並呼叫 AI 健檢..." : "更新履歷並獲取最新 AI 健檢建議"}
            </button>
          </form>

          {/* Gemini 履歷健檢結果 */}
          {suggestion && (
            <div
              className="mt-4 p-4 rounded-3"
              style={{
                background: "rgba(108, 140, 255, 0.08)",
                border: "1px solid rgba(108, 140, 255, 0.3)",
              }}
            >
              <p className="small mb-2" style={{ color: "var(--studio-accent)", fontWeight: 700 }}>
                ✨ AI 履歷健檢報告
              </p>
              <div style={{ whiteSpace: "pre-wrap", lineHeight: "1.7" }} className="small">
                {suggestion.replace(/\*\*/g, "").replace(/^\s*\*\s+/gm, "・")}
              </div>
            </div>
          )}

        </div>
      </Container>
    </div>
  );
}

export default function ResumePage() {
  return (
    <AuthGuard
      fallback={
        <div className="studio-bg d-flex justify-content-center align-items-center">
          <div className="studio-dim">安全性驗證中...</div>
        </div>
      }
    >
      <ResumePageContent />
    </AuthGuard>
  );
}
