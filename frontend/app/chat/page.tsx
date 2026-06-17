"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import InputBox from "./InputBox";
import ChatBody from "./chatBody"; // 注意：請確認您的檔案名稱大小寫是否正確
import Container from 'react-bootstrap/Container';

interface ChatContent {
    role: "user" | "Ai";
    content: string;
}

export default function Home() {
    const router = useRouter();
    const [chatContents, setChatContents] = useState<ChatContent[]>([]);
    const [loading, setLoading] = useState(false);
    
    // 驗證狀態與使用者 ID
    const [isAuth, setIsAuth] = useState(false);
    const [userId, setUserId] = useState<string>("");

    // 🌟 核心修正：阻擋瀏覽器上一頁/下一頁繞過登入的安全守衛
    useEffect(() => {
        const storedUser = sessionStorage.getItem("user");
        
        if (!storedUser) {
            // 如果沒有登入憑證，用 replace 強制替換歷史紀錄，徹底封鎖瀏覽器上下頁
            router.replace("/");
        } else {
            try {
                const user = JSON.parse(storedUser);
                if (user && user.id) {
                    setUserId(user.id);
                    setIsAuth(true); // 驗證成功，允許渲染畫面
                } else {
                    router.replace("/");
                }
            } catch (e) {
                router.replace("/");
            }
        }
    }, [router]);

    const handleSend = async (text: string) => {
        // 1️⃣ 先加使用者訊息
        setChatContents(prev => [...prev, { role: "user", content: text }]);
        setLoading(true);

        try {
            // 🌟 【關鍵修改】優先讀取 Vercel 上的環境變數，如果沒有才用 localhost
            const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            // 優先讀取環境變數，如果沒有才用 localhost
            const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

            // 將 userId 一併發送給後端，使 AI 能辨識身分、讀取履歷與對話記憶
            const res = await fetch(`${BACKEND_URL}/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    user_id: userId, 
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
                    // 【修改 2】這裡必須改成 data.response，因為您的 Python 是回傳 {"response": "..."}
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

    // 安全保護：在驗證未通過前不渲染任何內容，防止對話介面外洩
    if (!isAuth) {
        return (
            <div className="min-vh-100 bg-dark d-flex justify-content-center align-items-center">
                <div className="text-white-50">安全性驗證中...</div>
            </div>
        );
    }

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