// src/app/Header.tsx
"use client"; // 如果是用在 Next.js App Router 建議加上

import Container from 'react-bootstrap/Container';
import Navbar from 'react-bootstrap/Navbar';

export default function Header() {
  return (
    // 白色背景
    // 陰影效果
    <header className="bg-white shadow"> 
      {/* Container 自動處理最大寬度與置中 */}
      <Container className="py-4"> 
        {/* fw-bold: 粗體 */}
        {/* text-dark: 深色文字  */}
        {/* h2 或 display-*: 控制文字大小  */}
        <h1 className="fw-bold text-dark mb-0">
          AI 職涯教練平台
        </h1>
      </Container>
    </header>
  );
};
