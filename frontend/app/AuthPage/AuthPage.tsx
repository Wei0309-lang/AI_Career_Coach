"use client";
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
    <div className="card p-4 shadow-sm" style={{ width: "400px" }}>
      <h3 className="text-center mb-4">{isLogin ? "登入" : "註冊"}</h3>
      <form onSubmit={handleSubmit}>
        <input 
          type="email" placeholder="Email" className="form-control mb-2"
          value={email} onChange={(e) => setEmail(e.target.value)} required 
        />
        <input 
          type="password" placeholder="密碼" className="form-control mb-3"
          value={password} onChange={(e) => setPassword(e.target.value)} required 
        />
        <button className="btn btn-primary w-full mb-2">{isLogin ? "進入系統" : "立即註冊"}</button>
      </form>
      {error && <p className="text-danger text-sm">{error}</p>}
      <button onClick={() => setIsLogin(!isLogin)} className="btn btn-link btn-sm">
        {isLogin ? "沒有帳號？去註冊" : "已有帳號？去登入"}
      </button>
    </div>
  );
}