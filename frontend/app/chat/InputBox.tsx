"use client";

import { useState } from "react";
import Form from 'react-bootstrap/Form';
import Container from 'react-bootstrap/Container';

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
    // 1. fixed-bottom: 固定在視窗最下方
    // 2. bg-secondary: 灰色背景 
    // 3. py-3:上下內距
    <div className="fixed-bottom bg-dark py-3">
      {/* 輸入框置中、最大寬度*/}
      <Container className="d-flex justify-content-center">
  <Form.Control
    type="text"
    placeholder="輸入您的訊息..."
    value={input}
    onChange={(e) => setInput(e.target.value)}
    onKeyDown={handleKeyDown}
    className="rounded-pill border-0 shadow-sm px-4  bg-secondary text-white" 
    
    style={{ height: '50px', width: '100%', maxWidth: '800px' }} 
  />
</Container>
    </div>
  );
}
