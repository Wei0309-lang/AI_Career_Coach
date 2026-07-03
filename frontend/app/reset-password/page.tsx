"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "../lib/supabaseClient";

export default function ResetPasswordPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) setReady(true);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "PASSWORD_RECOVERY" || session) {
        setReady(true);
      }
    });

    return () => subscription.unsubscribe();
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
      setError(error.message);
      return;
    }

    setDone(true);
  };

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
