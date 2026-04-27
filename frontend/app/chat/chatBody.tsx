import React, { useState, useEffect, useRef } from 'react';
import Container from 'react-bootstrap/Container';
import Card from 'react-bootstrap/Card';

interface ChatContent {
    role: "user" | "Ai";
    content: string;
}

// 🛡️ Typewriter (打字機元件) - 強制切片版
const Typewriter = ({ text, speed }: { text: string, speed?: number }) => {
    const [displayedText, setDisplayedText] = useState("");

    // 這裡計算速度：如果有傳 speed 就用，沒傳就自動判斷 (字多跑得快)
    const typingSpeed = speed || (text.length > 50 ? 10 : 30);

    useEffect(() => {
        let currentIndex = 0;
        setDisplayedText(""); // 開始前先清空

        const intervalId = setInterval(() => {
            // 💡 關鍵修改：使用 slice (切片) 而不是 append (累加)
            // 這會強制文字等於原始資料的前 N 個字，就算插件亂改也會被這個強制修正回來
            setDisplayedText(text.slice(0, currentIndex + 1));

            currentIndex++;

            // 如果切片長度已經等於原始長度，就停止
            if (currentIndex >= text.length) {
                clearInterval(intervalId);
            }
        }, typingSpeed);

        return () => clearInterval(intervalId);
    }, [text, typingSpeed]);

    // 🛡️ 加上 translate="no" 和 className="notranslate" 
    // 這是給 Google/Edge 翻譯插件看的，叫它們不要碰這裡
    return (
        <span className="notranslate" translate="no">
            {displayedText}
        </span>
    );
};

export default function ChatBody({ chatContents, loading }: { chatContents: ChatContent[], loading: boolean }) {
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [chatContents, loading]);

    return (
        <div className="flex-grow-1 overflow-auto mb-3" style={{ maxHeight: '70vh' }}>
            {chatContents.map((msg, index) => (
                <div
                    key={index}
                    className={`d-flex mb-3 ${msg.role === 'user' ? 'justify-content-end' : 'justify-content-start'}`}
                >
                    <Card
                        className={`shadow-sm ${msg.role === 'user' ? 'bg-primary text-white' : 'bg-light text-dark'}`}
                        style={{ maxWidth: '75%', borderRadius: '15px' }}
                    >
                        {/* 🛡️ 在外層也加上防護罩，雙重保險 */}
                        <Card.Body className="p-3 notranslate" translate="no">
                            {/* 只有最新的一則 AI 訊息才使用打字機，其他的直接顯示以節省效能 */}
                            {msg.role === 'Ai' && index === chatContents.length - 1 ? (
                                <Typewriter text={msg.content} />
                            ) : (
                                msg.content
                            )}
                        </Card.Body>
                    </Card>
                </div>
            ))}

            {loading && (
                <div className="d-flex justify-content-start mb-3">
                    <Card className="bg-light text-dark shadow-sm" style={{ maxWidth: '75%', borderRadius: '15px' }}>
                        <Card.Body className="p-3">
                            <span className="spinner-grow spinner-grow-sm me-2" role="status" aria-hidden="true"></span>
                            AI 正在思考中...
                        </Card.Body>
                    </Card>
                </div>
            )}

            <div ref={messagesEndRef} />
        </div>
    );
}