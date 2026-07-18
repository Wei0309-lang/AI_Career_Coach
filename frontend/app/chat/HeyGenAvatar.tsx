"use client";
// HeyGenAvatar.tsx — HeyGen LiveAvatar 擬真虛擬面試官(Full Mode embed)
// 放在 frontend/app/chat/HeyGenAvatar.tsx
//
// 運作方式:掛載時向後端 /heygen/embed 要一個 iframe 網址,
// 之後的語音對話(ASR/LLM/TTS/影像)全部由 HeyGen 雲端在 iframe 內處理,
// 使用者直接對著它「講話」互動,不走我們自己的 /chat 文字流程。

import { useEffect, useState } from "react";
import { supabase } from "../lib/supabaseClient";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export default function HeyGenAvatar() {
  const [embedUrl, setEmbedUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sandbox, setSandbox] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session) throw new Error("尚未登入");

        const res = await fetch(`${BACKEND_URL}/heygen/embed`, {
          method: "POST",
          headers: { "Authorization": `Bearer ${session.access_token}` },
        });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || `HTTP ${res.status}`);
        }
        const data = await res.json();
        if (!cancelled) {
          setEmbedUrl(data.url);
          setSandbox(!!data.sandbox);
        }
      } catch (e: any) {
        console.error("❌ 取得 LiveAvatar embed 失敗:", e);
        if (!cancelled) setError(e.message || "未知錯誤");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div
      className="position-relative mx-auto mb-3 shadow"
      style={{
        width: "100%",
        maxWidth: "100%",
        aspectRatio: "16 / 9",
        borderRadius: "16px",
        overflow: "hidden",
        background: "#212529",
      }}
    >
      {embedUrl ? (
        <iframe
          src={embedUrl}
          allow="microphone"
          title="AI 面試官(LiveAvatar)"
          style={{ width: "100%", height: "100%", border: "none" }}
        />
      ) : error ? (
        <div className="position-absolute top-50 start-50 translate-middle text-white-50 small text-center px-3">
          擬真面試官載入失敗({error})
          <br />
          可將 NEXT_PUBLIC_AVATAR_MODE 改回 3d 使用備援模式
        </div>
      ) : (
        <div className="position-absolute top-50 start-50 translate-middle text-white text-center">
          <div className="spinner-border spinner-border-sm mb-2" role="status" />
          <div className="small">擬真面試官連線中...</div>
        </div>
      )}

      {sandbox && embedUrl && (
        <span
          className="position-absolute badge bg-warning text-dark"
          style={{ top: "12px", left: "12px" }}
        >
          Sandbox 測試模式
        </span>
      )}
    </div>
  );
}
