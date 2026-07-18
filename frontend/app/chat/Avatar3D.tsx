"use client";
// Avatar3D.tsx — 3D 虛擬面試官元件
// 放在 frontend/app/chat/Avatar3D.tsx
//
// 用法(在 chat/page.tsx):
//   const Avatar3D = dynamic(() => import("./Avatar3D"), { ssr: false });
//   <Avatar3D message={avatarMsg} />
//   每次 AI 回覆後 setAvatarMsg({ id: Date.now(), text: data.response })
//   虛擬人就會自動說出這段話並同步嘴型。
//
// 依賴:npm install three @met4citizen/talkinghead

import { useEffect, useRef, useState } from "react";
import { supabase } from "../lib/supabaseClient";

// Ready Player Me 模型網址。querystring 的 morphTargets 參數是關鍵:
// 沒有 Oculus Visemes 這組 blendshape,嘴巴就動不了。
// 之後你們可以到 https://readyplayer.me 捏一個自己的面試官,
// 把網址換掉即可(記得保留 ?morphTargets=... 之後的參數)。
const AVATAR_URL =
  process.env.NEXT_PUBLIC_AVATAR_GLB_URL ||
  "https://models.readyplayer.me/64bfa15f0e72c63d7c3934a6.glb" +
    "?morphTargets=ARKit,Oculus+Visemes,mouthOpen,mouthSmile,eyesClosed,eyesLookUp,eyesLookDown" +
    "&textureSizeLimit=1024&textureFormat=png";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

// Azure viseme ID(0-21)→ TalkingHead 使用的 Oculus viseme 名稱對照表
const AZURE_TO_OCULUS: string[] = [
  "sil", "aa", "aa", "O", "E",
  "E", "I", "U", "O", "aa",
  "O", "I", "kk", "RR", "nn",
  "SS", "SS", "TH", "FF", "DD",
  "kk", "PP",
];

export interface AvatarMessage {
  id: number; // 用時間戳當 id,確保同樣文字連續出現時也會觸發
  text: string;
}

interface Props {
  message: AvatarMessage | null;
}

export default function Avatar3D({ message }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const headRef = useRef<any>(null);
  const lastSpokenId = useRef<number>(0);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading"
  );
  const [speaking, setSpeaking] = useState(false);

  // ---------- 初始化:載入 TalkingHead 與 3D 模型(只跑一次) ----------
  useEffect(() => {
    let disposed = false;

    (async () => {
      try {
        // 動態 import:Three.js 只能在瀏覽器執行,避免 SSR 階段報錯
        const { TalkingHead } = await import(
        /* webpackIgnore: true */
        /* turbopackIgnore: true */
        "talkinghead");
        if (disposed || !containerRef.current) return;

        const head = new TalkingHead(containerRef.current, {
          // 我們用後端 Azure TTS(speakAudio 模式),不用內建 TTS,
          // 但這個參數是必填,給個佔位字串即可
          ttsEndpoint: "/unused",
          lipsyncModules: [],
          cameraView: "upper", // 上半身取景,像視訊面試
          avatarMood: "neutral",
        });

        await head.showAvatar({
          url: AVATAR_URL,
          body: "F",
          avatarMood: "neutral",
          lipsyncLang: "en",
        });

        if (disposed) return;
        headRef.current = head;
        (window as any).__head = head;   // 🆕 debug 用,之後可移除
        setStatus("ready");
      } catch (err) {
        console.error("❌ 3D 虛擬人初始化失敗:", err);
        if (!disposed) setStatus("error");
      }
    })();

    return () => {
      disposed = true;
      try {
        headRef.current?.stop?.();
      } catch {}
      headRef.current = null;
    };
  }, []);

  // ---------- 收到新的 AI 回覆 → 開口說話 ----------
  useEffect(() => {
    if (!message || status !== "ready") return;
    if (message.id === lastSpokenId.current) return; // 避免重複播放
    lastSpokenId.current = message.id;
    speak(message.text);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [message, status]);

  const speak = async (text: string) => {
    const head = headRef.current;
    if (!head) return;

    try {
      setSpeaking(true);

      // 瀏覽器 autoplay 政策:AudioContext 需在使用者互動後 resume。
      // 面試者剛按 Enter 送訊息,算互動,這裡 resume 一定成功。
      await head.audioCtx?.resume?.();

      // 1️⃣ 向後端取得語音 + 嘴型時間軸(需帶登入憑證，後端據此驗證身份)
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) throw new Error("尚未登入");

      const res = await fetch(`${BACKEND_URL}/avatar/tts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) throw new Error(`TTS API 錯誤: ${res.status}`);
      const data = await res.json();

      // 2️⃣ base64 mp3 → AudioBuffer
      const binary = atob(data.audio_base64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
      }
      const audioBuffer = await head.audioCtx.decodeAudioData(bytes.buffer);

     // 3️⃣ Azure viseme → TalkingHead 需要的三個陣列
      //    過濾掉靜音事件(id=0),比照官方範例作法
      const raw = (data.visemes as { id: number; offset_ms: number }[])
        .filter((v) => v.id !== 0);
      const visemes: string[] = [];
      const vtimes: number[] = [];
      const vdurations: number[] = [];
      raw.forEach((v, i, arr) => {
        visemes.push(AZURE_TO_OCULUS[v.id] ?? "sil");
        vtimes.push(v.offset_ms);
        const next = arr[i + 1];
        vdurations.push(next ? Math.max(next.offset_ms - v.offset_ms, 30) : 150);
      });

      // 4️⃣ 播放:TalkingHead 會同步驅動嘴型 blendshape
      //    ⚠️ words 陣列必須存在(即使是空字串),否則函式庫會直接略過 visemes
      //    (talkinghead.mjs 第 3112 行:整個 viseme 處理包在 if (r.words) 裡)
      head.speakAudio(
        {
          audio: audioBuffer,
          words: [""],
          wtimes: [0],
          wdurations: [0],
          visemes,
          vtimes,
          vdurations,
        },
        {},
        () => {}
      );

      // 粗估說完的時間點,把「說話中」狀態關掉
      const durationMs = audioBuffer.duration * 1000;
      setTimeout(() => setSpeaking(false), durationMs + 500);
    } catch (err) {
      console.error("❌ 語音播放失敗:", err);
      setSpeaking(false);
    }
  };

  return (
    <div
      className="position-relative mx-auto mb-3 shadow"
      style={{
        width: "100%",
        aspectRatio: "16 / 9",
        borderRadius: "16px",
        overflow: "hidden",
        background: "#212529",
      }}
    >
      {/* TalkingHead 會把 WebGL canvas 掛進這個 div */}
      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />

      {status === "loading" && (
        <div className="position-absolute top-50 start-50 translate-middle text-white text-center">
          <div className="spinner-border spinner-border-sm mb-2" role="status" />
          <div className="small">3D 面試官載入中...</div>
        </div>
      )}
      {status === "error" && (
        <div className="position-absolute top-50 start-50 translate-middle text-white-50 small text-center px-3">
          3D 虛擬人載入失敗,面試仍可正常以文字進行
        </div>
      )}
      {speaking && (
        <span
          className="position-absolute badge bg-danger"
          style={{ top: "12px", right: "12px" }}
        >
          ● 面試官發言中
        </span>
      )}
    </div>
  );
}
