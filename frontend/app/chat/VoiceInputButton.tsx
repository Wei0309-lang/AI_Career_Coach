"use client";
// VoiceInputButton.tsx — 語音輸入按鈕(Web Speech API,zh-TW)
// 放在 frontend/app/chat/VoiceInputButton.tsx
//
// 用法:在 InputBox.tsx 的輸入框旁邊放
//   <VoiceInputButton onResult={(text) => setInput(prev => prev + text)} />
// 按一下開始收音(按鈕變紅),辨識到的中文會透過 onResult 回傳;
// 再按一下或停頓幾秒自動結束。
//
// 使用 Chrome/Edge 內建語音辨識,免費、免金鑰、免後端。
// Firefox/Safari 不支援時按鈕會自動隱藏,不影響打字輸入。

import { useEffect, useRef, useState } from "react";

interface Props {
  onResult: (text: string) => void; // 辨識完成的文字(每句話回傳一次)
}

export default function VoiceInputButton({ onResult }: Props) {
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    // Chrome 是 webkitSpeechRecognition,標準名稱是 SpeechRecognition
    const SR =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    if (!SR) return; // 瀏覽器不支援 → 按鈕不顯示

    const recognition = new SR();
    recognition.lang = "zh-TW";          // 繁體中文(台灣)
    recognition.continuous = false;      // 講完一句自動停止
    recognition.interimResults = false;  // 只回傳最終結果,避免文字跳動

    recognition.onresult = (event: any) => {
      const transcript = Array.from(event.results)
        .map((r: any) => r[0].transcript)
        .join("");
      if (transcript) onResult(transcript);
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = (e: any) => {
      console.error("語音辨識錯誤:", e.error);
      setListening(false);
    };

    recognitionRef.current = recognition;
    setSupported(true);

    return () => {
      try {
        recognition.abort();
      } catch {}
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggle = () => {
    const recognition = recognitionRef.current;
    if (!recognition) return;
    if (listening) {
      recognition.stop();
      setListening(false);
    } else {
      try {
        recognition.start(); // 第一次會跳出麥克風權限請求
        setListening(true);
      } catch {
        // 連點兩下等造成的重複 start,忽略即可
      }
    }
  };

  if (!supported) return null;

  return (
    <button
      type="button"
      onClick={toggle}
      className={`btn ${listening ? "btn-danger" : "btn-outline-secondary"} rounded-circle d-flex align-items-center justify-content-center`}
      style={{ width: "42px", height: "42px", flexShrink: 0 }}
      title={listening ? "停止收音" : "語音輸入"}
      aria-label={listening ? "停止收音" : "語音輸入"}
    >
      {/* 麥克風 icon(inline SVG,不需額外套件) */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="18"
        height="18"
        fill="currentColor"
        viewBox="0 0 16 16"
      >
        <path d="M5 3a3 3 0 0 1 6 0v5a3 3 0 0 1-6 0V3z" />
        <path d="M3.5 6.5A.5.5 0 0 1 4 7v1a4 4 0 0 0 8 0V7a.5.5 0 0 1 1 0v1a5 5 0 0 1-4.5 4.975V15h3a.5.5 0 0 1 0 1h-7a.5.5 0 0 1 0-1h3v-2.025A5 5 0 0 1 3 8V7a.5.5 0 0 1 .5-.5z" />
      </svg>
    </button>
  );
}
