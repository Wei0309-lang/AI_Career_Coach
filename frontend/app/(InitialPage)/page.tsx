"use client";
import { useState, useEffect } from "react";
import AuthPage from "../AuthPage/AuthPage";
import MainButton from "./MainButton";

export default function Dashboard() {
  const [user, setUser] = useState<any>(null);
  const [checking, setChecking] = useState(true);

  // 頁面載入時，檢查是否有憑證（統一改為 sessionStorage）
  useEffect(() => {
    const savedUser = sessionStorage.getItem("user");
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
    setChecking(false);
  }, []);

  const handleLogin = (userData: any) => {
    setUser(userData);
    // 這裡由 AuthPage 寫入 sessionStorage，但保險起見這裡也同步確保存在
    sessionStorage.setItem("user", JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
    // 🌟 核心修正：確實清除對話頁面檢查的憑證
    sessionStorage.removeItem("user");
  };

  if (checking) {
    return (
      <div className="min-vh-100 bg-primary-subtle d-flex justify-content-center align-items-center">
        <div className="text-dark">載入中...</div>
      </div>
    );
  }

  return (
    <div className="min-vh-100 bg-primary-subtle d-flex flex-column">
      <div className="container py-5 text-center flex-grow-1">
        {!user ? (
          <div className="d-flex flex-column align-items-center mt-5">
            <h2 className="mb-4 text-dark">歡迎使用 AI 職涯導師，請先登入</h2>
            <AuthPage onLoginSuccess={handleLogin} />
          </div>
        ) : (
          <div className="mt-5">
            <h1 className="display-4 text-primary fw-bold">您的 AI 職涯導師</h1>
            <p className="lead mt-3 text-secondary">您好 {user.email}，準備好開始面試了嗎？</p>
            <div className="mt-5">
              <MainButton />
            </div>
            <button onClick={handleLogout} className="btn btn-outline-secondary btn-sm mt-5">
              登出系統
            </button>
          </div>
        )}
      </div>
    </div>
  );
}