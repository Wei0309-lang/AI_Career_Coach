"use client";

import { useState } from "react";
import InputBox from "./InputBox";
import ChatBody from "./chatBody"; // 注意：請確認您的檔案名稱大小寫是否正確
import Container from 'react-bootstrap/Container';
import AuthGuard from "../components/AuthGuard";
import { supabase } from "../lib/supabaseClient";

interface ChatContent {
    role: "user" | "Ai";
    content: string;
}

function ChatPageContent() {
    const [chatContents, setChatContents] = useState<ChatContent[]>([]);
    const [loading, setLoading] = useState(false);

    const handleSend = async (text: string) => {
        // 1️⃣ 先加使用者訊息
        setChatContents(prev => [...prev, { role: "user", content: text }]);
        setLoading(true);

        try {
            // 優先讀取環境變數，如果沒有才用 localhost
            const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

            const { data: { session } } = await supabase.auth.getSession();
            if (!session) {
                throw new Error("尚未登入");
            }

            // 用登入憑證（JWT）辨識身分，後端據此讀取履歷與對話記憶
            const res = await fetch(`${BACKEND_URL}/chat`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${session.access_token}`,
                },
                body: JSON.stringify({
                    message: text
                }),
            });

            if (!res.ok) {
                throw new Error(`HTTP error! status: ${res.status}`);
            }

            const data = await res.json();

            // 建議加入這行 Log，方便您在 F12 Console 檢查後端到底回傳了什麼
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

export default function Home() {
    return (
        <AuthGuard
            fallback={
                <div className="min-vh-100 bg-dark d-flex justify-content-center align-items-center">
                    <div className="text-white-50">安全性驗證中...</div>
                </div>
            }
        >
            <ChatPageContent />
        </AuthGuard>
    );
}
