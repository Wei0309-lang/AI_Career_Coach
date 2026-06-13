"use client";

import { useState } from "react";
import InputBox from "./InputBox";
import ChatBody from "./chatBody"; // 注意：請確認您的檔案名稱大小寫是否正確
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
            // 【修改 1】建議使用 127.0.0.1 取代 localhost，避免 Windows 解析錯誤
            const res = await fetch("http://localhost:8001/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text }),
            });

            if (!res.ok) {
                throw new Error(`HTTP error! status: ${res.status}`);
            }

            const data = await res.json();

            // Log，F12 Console可檢查後端到底回傳了什麼
            console.log("後端回傳資料:", data);

            // 2️⃣ 加 AI 回覆
            setChatContents(prev => [
                ...prev,
                {
                    role: "Ai",
                    content: data.response
                },
            ]);
        } catch (error) {
            console.error("連線錯誤:", error);
            setChatContents(prev => [
                ...prev,
                { role: "Ai", content: "無法連接到後端服務器，請檢查 Port 8001 是否運行中，並確認 Main.py 已啟動。" },
            ]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-vh-100 d-flex flex-column bg-dark">
            <Container className="p-4 flex-grow-1 d-flex flex-column">
                <h1 className="display-5 fw-bold mb-4 text-white-50 text-center">
                    AI 職涯教練平台
                </h1>

                <ChatBody chatContents={chatContents} loading={loading} />

            </Container>

            <InputBox onSend={handleSend} />
        </div>
    );
}