"use client";

import { useState } from "react";
import InputBox from "./InputBox";
import ChatBody from "./chatBody";
import Container from 'react-bootstrap/Container';

interface ChatContent {
  role: "user" | "Ai";
  content: string;
}

export default function Home() {
  const [chatContents, setChatContents] = useState<ChatContent[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSend = async (text: string) => {
    // 1️⃣ 先加使用者訊息
    setChatContents(prev => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      // 確保你的後端 (Port 8001) 有打開喔！
      const response = await fetch("http://localhost:8001/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });

      const data = await response.json();

      // 2️⃣ 加 AI 回覆
      setChatContents(prev => [
        ...prev,
        { role: "Ai", content: data.message },
      ]);
    } catch (error) {
      setChatContents(prev => [
        ...prev,
        { role: "Ai", content: "無法連接到後端服務器，請檢查 Port 8001 是否運行中。" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    // 1. min-vh-100: 高度至少 100% 視窗高度 (取代 min-h-screen)
    // 2. d-flex flex-column: 讓內容垂直排列，這樣 ChatBody 才能長高 (取代 flex flex-col)
    // 3. bg-dark: 深色背景 (取代 bg-gray-700)
    <div className="min-vh-100 d-flex flex-column bg-dark">
      
      <Container className="p-4 flex-grow-1 d-flex flex-column">
        {/* 標題區域 */}
        {/* text-white-50: 半透明白色文字 (取代 text-gray-400) */}
        <h1 className="display-5 fw-bold mb-4 text-white-50 text-center">
          AI 職涯教練平台
        </h1>

        {/* 聊天內容區域 */}
        {/* 把剩下的空間都分給 ChatBody */}
        <ChatBody chatContents={chatContents} loading={loading} />
        
      </Container>

      {/* 輸入框 (因為 InputBox 內部我們寫了 fixed-bottom，所以這裡直接放著就好) */}
      <InputBox onSend={handleSend} />
    </div>
  );
}
