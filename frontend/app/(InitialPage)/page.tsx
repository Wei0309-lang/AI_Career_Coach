"use client";
import { useState, useEffect } from "react";
import AuthPage from "../AuthPage/AuthPage";
import MainButton from "./MainButton";
import { supabase } from "../lib/supabaseClient";

type User = { id: string; email: string };

export default function Dashboard() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ? { id: session.user.id, email: session.user.email ?? "" } : null);
      setChecking(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ? { id: session.user.id, email: session.user.email ?? "" } : null);
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleLogin = (userData: User) => {
    setUser(userData);
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    setUser(null);
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

            {/* 畫面中央的功能按鈕群組，履歷健檢已內嵌於此元件內部 */}
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
