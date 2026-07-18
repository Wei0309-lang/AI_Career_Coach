"use client";
// ResumeUpload.tsx — 履歷 PDF 上傳與 AI 自動解析(Gemini 原生解析 PDF)
// 目前尚未掛載於任何頁面；/api/resume/upload 已改為 JWT 驗證身份，
// 若要在其他畫面使用本元件，直接引入即可，不需再傳入 userId。
//   <ResumeUpload onParsed={() => window.location.reload()} />
// (onParsed 觸發重新整理,頁面原有的「載入既有履歷」邏輯會自動把解析結果填入表單)

import { useRef, useState } from "react";
import { supabase } from "../lib/supabaseClient";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface Props {
  onParsed?: () => void;
}

export default function ResumeUpload({ onParsed }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string>("");

  const handleFile = async (file: File) => {
    if (!file) return;
    if (file.type !== "application/pdf") {
      setMessage("❌ 請選擇 PDF 檔案");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setMessage("❌ 檔案過大,請小於 10MB");
      return;
    }

    setUploading(true);
    setMessage("");
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        setMessage("❌ 尚未登入");
        return;
      }

      const form = new FormData();
      form.append("file", file);

      const res = await fetch(`${BACKEND_URL}/api/resume/upload`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${session.access_token}` },
        body: form, // multipart:不要手動設 Content-Type,瀏覽器會自帶 boundary
      });
      const data = await res.json();
      if (!res.ok) {
        setMessage(`❌ ${data.detail || "解析失敗,請再試一次"}`);
        return;
      }
      setMessage("✅ 履歷解析完成,已自動填入表單");
      onParsed?.();
    } catch (e) {
      console.error("履歷上傳失敗:", e);
      setMessage("❌ 連線失敗,請確認後端服務正常");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div className="mb-4 p-3 rounded-3 text-center"
      style={{ border: "1px dashed rgba(255,255,255,.25)" }}>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        style={{ display: "none" }}
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />
      <p className="small mb-2" style={{ opacity: 0.75 }}>
        懶得手動填寫？上傳履歷 PDF,AI 會自動解析並填入下方表單
      </p>
      <button
        type="button"
        className="btn btn-outline-primary btn-sm px-4"
        disabled={uploading}
        onClick={() => inputRef.current?.click()}
      >
        {uploading ? "AI 解析中,約需 10 秒..." : "📄 上傳履歷 PDF"}
      </button>
      {message && <p className="small mt-2 mb-0">{message}</p>}
    </div>
  );
}
