"use client";

"use client";
import { useState } from "react";
import InputBox from "./InputBox";
import ChatBody from "./chatBody";

interface ChatContent {
  role: "user" | "Ai";
  content: string;
}

export default function Home() {
  const [chatContents, setChatContents] = useState<ChatContent[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSend = async (text: string) => {
    //  先加使用者訊息
    setChatContents(prev => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
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
        { role: "Ai", content: "無法連接到後端服務器" },
      ]);
    } finally {
      setLoading(false);
    }
  };




  return (
    <div className="min-h-screen flex flex-col bg-gray-700 p-10">
      <h1 className="text-4xl font-bold mb-6 text-gray-400">
        AI 職涯教練平台
      </h1>

      <ChatBody chatContents={chatContents} loading={loading} />
      <InputBox onSend={handleSend} />
    </div>
  );
}
