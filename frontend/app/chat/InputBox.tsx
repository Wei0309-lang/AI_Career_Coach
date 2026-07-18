"use client";

import { useState } from "react";
import Form from 'react-bootstrap/Form';
import Container from 'react-bootstrap/Container';
import Button from 'react-bootstrap/Button';
import VoiceInputButton from "./VoiceInputButton";

interface InputBoxProps {
  onSend: (message: string) => void;
}

export default function InputBox({ onSend }: InputBoxProps) {
  const [input, setInput] = useState("");

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      // 防止中文輸入法選字時誤傳送
      if (e.nativeEvent.isComposing) {
        return;
      }
      e.preventDefault();
      handleSend();
    }
  }

  const handleSend = () => {
    if (input.trim() === "") {
      return;
    }
    if (onSend && input.trim() !== "") {
      onSend(input.trim());
      setInput("");
    }
  }

  return (
    // 主題化:studio-inputbar = 半透明毛玻璃 + 上緣分隔線
    <div className="fixed-bottom studio-inputbar py-3">
      <Container className="d-flex justify-content-center align-items-center gap-2">

        {/* 語音輸入:辨識文字接到現有內容後面,可再編輯後才送出 */}
        <VoiceInputButton
          onResult={(spoken) =>
            setInput((prev) => (prev ? prev + " " + spoken : spoken))
          }
        />

        <Form.Control
          type="text"
          placeholder="輸入您的訊息，或按左側麥克風用說的..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          className="studio-input rounded-pill px-4"
          style={{ height: '50px', width: '100%', maxWidth: '800px' }}
        />

        {/* 送出鈕:語音輸入後不用回鍵盤按 Enter,直接點擊送出 */}
        <Button
          className="btn-studio rounded-pill px-4 flex-shrink-0"
          style={{ height: '50px' }}
          onClick={handleSend}
          disabled={!input.trim()}
        >
          送出
        </Button>

      </Container>
    </div>
  );
}
