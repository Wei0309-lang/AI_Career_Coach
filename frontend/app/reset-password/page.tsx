"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "../lib/supabaseClient";
import { translateAuthError } from "../lib/authErrors";

// 等待 Supabase 從連結中換出 session 的上限時間；超過就視為連結無效/已過期，
// 不再讓使用者永遠卡在轉圈圈畫面
const RECOVERY_TIMEOUT_MS = 8000;

export default function ResetPasswordPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [linkError, setLinkError] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    // 連結無效/過期時，Supabase 會把錯誤原因帶在 URL hash 上（例如
    // #error=access_denied&error_code=otp_expired&error_description=...），
    // 而不是觸發任何 session 事件，因此要主動解析、不能只等 onAuthStateChange
    const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const errorDescription = hashParams.get("error_description");
    if (errorDescription) {
      setLinkError(decodeURIComponent(errorDescription.replace(/\+/g, " ")));
      return;
    }

    let settled = false;

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session && !settled) {
        settled = true;
        setReady(true);
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if ((event === "PASSWORD_RECOVERY" || session) && !settled) {
        settled = true;
        setReady(true);
      }
    });

    // 保底：連結失效時 Supabase 有時不會帶 error 參數，也不會觸發任何事件，
    // 純粹讓頁面停在讀取中，超時就主動改判為連結失效
    const timeout = window.setTimeout(() => {
      if (!settled) {
        setLinkError("重設密碼連結無效或已過期，請重新申請一次。");
      }
    }, RECOVERY_TIMEOUT_MS);

    return () => {
      subscription.unsubscribe();
      window.clearTimeout(timeout);
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("兩次輸入的密碼不一致");
      return;
    }

    const { error } = await supabase.auth.updateUser({ password });

    if (error) {
      setError(translateAuthError(error.message));
      return;
    }

    setDone(true);
  };

  if (linkError) {
    return (
      <div className="min-vh-100 d-flex flex-column justify-content-center align-items-center text-center px-3">
        <p className="mb-3 text-danger">{linkError}</p>
        <button className="btn btn-primary" onClick={() => router.push("/")}>
          返回登入頁面重新申請
        </button>
      </div>
    );
  }

  if (!ready) {
    return (
      <div className="min-vh-100 d-flex justify-content-center align-items-center">
        <div className="spinner-border text-primary" role="status"></div>
      </div>
    );
  }

  if (done) {
    return (
      <div className="min-vh-100 d-flex flex-column justify-content-center align-items-center">
        <p className="mb-3">密碼已重設成功！</p>
        <button className="btn btn-primary" onClick={() => router.push("/")}>
          返回登入頁面
        </button>
      </div>
    );
  }

  return (
    <div className="min-vh-100 d-flex justify-content-center align-items-center">
      <div className="card p-4 shadow-sm" style={{ width: "400px" }}>
        <h3 className="text-center mb-4">設定新密碼</h3>
        <form onSubmit={handleSubmit}>
          <input
            type="password" placeholder="新密碼" className="form-control mb-2"
            value={password} onChange={(e) => setPassword(e.target.value)} required
          />
          <input
            type="password" placeholder="確認新密碼" className="form-control mb-3"
            value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required
          />
          <button className="btn btn-primary w-100">更新密碼</button>
        </form>
        {error && <p className="text-danger text-sm mt-2">{error}</p>}
      </div>
    </div>
  );
}
