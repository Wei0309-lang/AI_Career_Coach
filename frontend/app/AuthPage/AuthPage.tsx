"use client";
import { useState } from "react";
import { supabase } from "../lib/supabaseClient";

type User = { id: string; email: string };
type Mode = "login" | "register" | "forgot";

function translateAuthError(message: string): string {
  const lower = message.toLowerCase();
  if (lower.includes("already registered") || lower.includes("already exists")) {
    return "此 Email 已被註冊，請直接登入或使用忘記密碼功能。";
  }
  if (lower.includes("invalid login credentials")) {
    return "帳號或密碼錯誤。";
  }
  if (lower.includes("email not confirmed")) {
    return "此帳號尚未完成信件驗證，請先至信箱點擊驗證連結。";
  }
  return message;
}

export default function AuthPage({ onLoginSuccess }: { onLoginSuccess: (user: User) => void }) {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const switchMode = (next: Mode) => {
    setMode(next);
    setError("");
    setNotice("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setNotice("");

    try {
      if (mode === "login") {
        const { data, error } = await supabase.auth.signInWithPassword({ email, password });

        if (error) {
          setError(translateAuthError(error.message));
          return;
        }

        if (data.user) {
          onLoginSuccess({ id: data.user.id, email: data.user.email ?? email });
        }
      } else if (mode === "register") {
        const { error } = await supabase.auth.signUp({ email, password });

        if (error) {
          setError(translateAuthError(error.message));
          return;
        }

        alert("註冊成功，請至信箱點擊驗證連結完成開通！");
        switchMode("login");
      } else {
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo: `${window.location.origin}/reset-password`,
        });

        if (error) {
          setError(translateAuthError(error.message));
          return;
        }

        setNotice("若此信箱已註冊，重設密碼信件已寄出，請至信箱查收。");
      }
    } catch {
      setError("連線 Supabase 失敗");
    }
  };

  const titleMap: Record<Mode, string> = {
    login: "登入",
    register: "註冊",
    forgot: "忘記密碼",
  };

  return (
    <div className="card p-4 shadow-sm" style={{ width: "400px" }}>
      <h3 className="text-center mb-4">{titleMap[mode]}</h3>
      <form onSubmit={handleSubmit}>
        <input
          type="email" placeholder="Email" className="form-control mb-2"
          value={email} onChange={(e) => setEmail(e.target.value)} required
        />
        {mode !== "forgot" && (
          <input
            type="password" placeholder="密碼" className="form-control mb-3"
            value={password} onChange={(e) => setPassword(e.target.value)} required
          />
        )}
        <button className="btn btn-primary w-full mb-2">
          {mode === "login" ? "進入系統" : mode === "register" ? "立即註冊" : "寄送重設密碼信件"}
        </button>
      </form>

      {error && <p className="text-danger text-sm">{error}</p>}
      {notice && <p className="text-success text-sm">{notice}</p>}

      {mode === "login" && (
        <div className="d-flex flex-column">
          <button onClick={() => switchMode("register")} className="btn btn-link btn-sm">
            沒有帳號？去註冊
          </button>
          <button onClick={() => switchMode("forgot")} className="btn btn-link btn-sm">
            忘記密碼？
          </button>
        </div>
      )}
      {mode === "register" && (
        <button onClick={() => switchMode("login")} className="btn btn-link btn-sm">
          已有帳號？去登入
        </button>
      )}
      {mode === "forgot" && (
        <button onClick={() => switchMode("login")} className="btn btn-link btn-sm">
          返回登入
        </button>
      )}
    </div>
  );
}
