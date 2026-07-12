"use client";
// AuthPage.tsx — 「面試等候室」風格登入/註冊面板
// 邏輯與原版完全相同(handleSubmit、sessionStorage、錯誤處理皆未更動),僅調整外觀。
import { useState } from "react";

type User = { id: string; email: string };

export default function AuthPage({ onLoginSuccess }: { onLoginSuccess: (user: User) => void }) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const url = isLogin ? "/api/login" : "/api/register";

    try {
      const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

      console.log("準備打的網址是：", `${BACKEND_URL}${url}`);
      const response = await fetch(`${BACKEND_URL}${url}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (response.ok) {
        if (isLogin) {
          // 登入成功時，將使用者資料寫入記錄中
          sessionStorage.setItem("user", JSON.stringify(data.user));
          onLoginSuccess(data.user);
        } else {
          // 🌟 核心修正：將寫死的文字改為讀取後端發信成功的引導訊息
          alert(data.message || "註冊成功，請至信箱啟用帳號！");
          setIsLogin(true);
        }
      } else {
        setError(data.detail || "操作失敗");
      }
    } catch {
      setError("連線後端失敗");
    }
  };

  return (
    <div className="studio-panel p-4 p-md-5" style={{ width: "100%", maxWidth: "420px" }}>
      <div className="text-center mb-4">
        <span className="studio-eyebrow">Interview Room</span>
        <h3 className="studio-title mt-2 mb-1">{isLogin ? "進入面試室" : "建立帳號"}</h3>
        <p className="studio-dim small mb-0">
          {isLogin ? "登入後即可開始您的模擬面試" : "註冊後請至信箱點擊驗證信啟用帳號"}
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        <input
          type="email" placeholder="Email" className="form-control studio-input mb-3"
          value={email} onChange={(e) => setEmail(e.target.value)} required
        />
        <input
          type="password" placeholder="密碼" className="form-control studio-input mb-4"
          value={password} onChange={(e) => setPassword(e.target.value)} required
        />
        <button className="btn btn-studio w-100 mb-2">
          {isLogin ? "進入系統" : "立即註冊"}
        </button>
      </form>

      {error && (
        <p className="small text-center mt-2 mb-0" style={{ color: "var(--studio-rec)" }}>
          {error}
        </p>
      )}

      <div className="text-center mt-3">
        <button
          onClick={() => setIsLogin(!isLogin)}
          className="btn btn-link btn-sm text-decoration-none"
          style={{ color: "var(--studio-accent)" }}
        >
          {isLogin ? "沒有帳號？去註冊" : "已有帳號？去登入"}
        </button>
      </div>
    </div>
  );
}
