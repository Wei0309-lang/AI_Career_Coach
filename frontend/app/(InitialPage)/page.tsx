"use client";
// app/(InitialPage)/page.tsx — 首頁(登入前/後)
// 邏輯與原版完全相同(sessionStorage 檢查、登入/登出處理皆未更動),僅調整外觀。
import { useState, useEffect } from "react";
import AuthPage from "../AuthPage/AuthPage";
import MainButton from "./MainButton";

export default function Dashboard() {
  const [user, setUser] = useState<any>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const savedUser = sessionStorage.getItem("user");
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
    setChecking(false);
  }, []);

  const handleLogin = (userData: any) => {
    setUser(userData);
    sessionStorage.setItem("user", JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
    sessionStorage.removeItem("user");
  };

  if (checking) {
    return (
      <div className="studio-bg d-flex justify-content-center align-items-center">
        <div className="studio-dim">載入中...</div>
      </div>
    );
  }

  return (
    <div className="studio-bg d-flex flex-column">
      <div className="container py-5 text-center flex-grow-1 d-flex flex-column justify-content-center">
        {!user ? (
          <div className="d-flex flex-column align-items-center">
            <span className="studio-eyebrow mb-2">AI Career Coach</span>
            <h2 className="studio-title mb-4">歡迎使用 AI 職涯導師</h2>
            <AuthPage onLoginSuccess={handleLogin} />
          </div>
        ) : (
          <div>
            <span className="studio-eyebrow">AI Career Coach</span>
            <h1
              className="studio-title mt-2"
              style={{ fontSize: "clamp(2rem, 5vw, 3.2rem)" }}
            >
              您的 AI 職涯導師
            </h1>
            <p className="studio-dim mt-3">
              您好 <span style={{ color: "var(--studio-text)" }}>{user.email}</span>
              ，準備好開始面試了嗎？
            </p>

            {/* 畫面中央的功能按鈕群組，履歷健檢已內嵌於此元件內部 */}
            <div className="mt-5">
              <MainButton />
            </div>

            <button onClick={handleLogout} className="btn btn-studio-ghost btn-sm mt-5 px-4">
              登出系統
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
