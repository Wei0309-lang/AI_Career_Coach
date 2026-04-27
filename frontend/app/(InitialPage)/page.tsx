"use client";
import { useState, useEffect } from "react";
import AuthPage from "../AuthPage/AuthPage";
import MainButton from "./MainButton";

export default function Dashboard() {
  const [user, setUser] = useState<any>(null);

  // 頁面載入時，檢查是否有舊的登入紀錄
  useEffect(() => {
    const savedUser = localStorage.getItem("interview_user");
    if (savedUser) setUser(JSON.parse(savedUser));
  }, []);

  const handleLogin = (userData: any) => {
    setUser(userData);
    localStorage.setItem("interview_user", JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem("interview_user");
  };

  return (
    // 🌟 這裡新增了最外層的 wrapper，設定最小高度 100vh 以及淺色背景
    <div className="min-vh-100 bg-primary-subtle d-flex flex-column">
      {/* 原本的 container 放在裡面，並微調一下間距 */}
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