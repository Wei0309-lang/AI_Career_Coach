"use client";
// AuthPage.tsx — 「面試等候室」風格登入/註冊面板
import { useState } from "react";
import { supabase } from "../lib/supabaseClient";
import { translateAuthError } from "../lib/authErrors";

type User = { id: string; email: string };
type Mode = "login" | "register" | "forgot";

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
        } else {
          setError("登入失敗，請再試一次。");
        }
      } else if (mode === "register") {
        const { data, error } = await supabase.auth.signUp({ email, password });

        if (error) {
          setError(translateAuthError(error.message));
          return;
        }

        // Supabase 為防止帳號枚舉攻擊，對「已註冊且已驗證」的 email 重複註冊時
        // 不會回傳 error，而是回傳成功但 identities 為空陣列，須由此判斷是否為舊帳號
        if (data.user && data.user.identities && data.user.identities.length === 0) {
          setError("此 Email 已被註冊，請直接登入或使用忘記密碼功能。");
          return;
        }

        // 若專案設定為「免信箱驗證」(auto-confirm)，signUp 會直接帶回已登入的 session
        if (data.session && data.user) {
          onLoginSuccess({ id: data.user.id, email: data.user.email ?? email });
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

  const subtitleMap: Record<Mode, string> = {
    login: "登入後即可開始您的模擬面試",
    register: "註冊後請至信箱點擊驗證信啟用帳號",
    forgot: "輸入註冊時使用的 Email，我們會寄送重設密碼的連結",
  };

  return (
    <div className="studio-panel p-4 p-md-5" style={{ width: "100%", maxWidth: "420px" }}>
      <div className="text-center mb-4">
        <span className="studio-eyebrow">Interview Room</span>
        <h3 className="studio-title mt-2 mb-1">
          {mode === "login" ? "進入面試室" : mode === "register" ? "建立帳號" : "忘記密碼"}
        </h3>
        <p className="studio-dim small mb-0">{subtitleMap[mode]}</p>
      </div>

      <form onSubmit={handleSubmit}>
        <input
          type="email" placeholder="Email" className="form-control studio-input mb-3"
          value={email} onChange={(e) => setEmail(e.target.value)} required
        />
        {mode !== "forgot" && (
          <input
            type="password" placeholder="密碼" className="form-control studio-input mb-4"
            value={password} onChange={(e) => setPassword(e.target.value)} required
          />
        )}
        <button className="btn btn-studio w-100 mb-2">
          {mode === "login" ? "進入系統" : mode === "register" ? "立即註冊" : "寄送重設密碼信件"}
        </button>
      </form>

      {error && (
        <p className="small text-center mt-2 mb-0" style={{ color: "var(--studio-rec)" }}>
          {error}
        </p>
      )}
      {notice && (
        <p className="small text-center mt-2 mb-0" style={{ color: "var(--studio-accent)" }}>
          {notice}
        </p>
      )}

      <div className="text-center mt-3 d-flex flex-column gap-1">
        {mode === "login" && (
          <>
            <button
              onClick={() => switchMode("register")}
              className="btn btn-link btn-sm text-decoration-none"
              style={{ color: "var(--studio-accent)" }}
            >
              沒有帳號？去註冊
            </button>
            <button
              onClick={() => switchMode("forgot")}
              className="btn btn-link btn-sm text-decoration-none"
              style={{ color: "var(--studio-accent)" }}
            >
              忘記密碼？
            </button>
          </>
        )}
        {mode === "register" && (
          <button
            onClick={() => switchMode("login")}
            className="btn btn-link btn-sm text-decoration-none"
            style={{ color: "var(--studio-accent)" }}
          >
            已有帳號？去登入
          </button>
        )}
        {mode === "forgot" && (
          <button
            onClick={() => switchMode("login")}
            className="btn btn-link btn-sm text-decoration-none"
            style={{ color: "var(--studio-accent)" }}
          >
            返回登入
          </button>
        )}
      </div>
    </div>
  );
}
