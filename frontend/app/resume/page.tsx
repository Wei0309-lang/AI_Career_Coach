"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Container from "react-bootstrap/Container";

export default function ResumePage() {
  const router = useRouter();
  const [userId, setUserId] = useState<string>("");
  const [isAuth, setIsAuth] = useState(false);
  const [loading, setLoading] = useState(false);
  const [suggestion, setSuggestion] = useState<string>("");

  // 表單資料狀態
  const [formData, setFormData] = useState({
    fullName: "",
    summary: "",
    skills: "",
    experience: "",
  });

  // 🌟 安全守衛：檢查是否已登入
  useEffect(() => {
    const storedUser = sessionStorage.getItem("user");
    if (!storedUser) {
      router.replace("/");
    } else {
      try {
        const user = JSON.parse(storedUser);
        if (user && user.id) {
          setUserId(user.id);
          setIsAuth(true);
        } else {
          router.replace("/");
        }
      } catch (e) {
        router.replace("/");
      }
    }
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setSuggestion("");

    try {
      const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
      
      // 呼叫後端 /api/resume 儲存資料並獲取 Gemini 建議
      const response = await fetch(`${BACKEND_URL}/api/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          ...formData,
        }),
      });

      if (!response.ok) {
        throw new Error("伺服器錯誤");
      }

      const data = await response.json();
      setSuggestion(data.suggestion);
      
    } catch (err) {
      setSuggestion("❌ 儲存失敗或 AI 健檢服務暫時無法使用，請檢查連線。");
    } finally {
      setLoading(false);
    }
  };

  if (!isAuth) {
    return (
      <div className="min-vh-100 bg-light d-flex justify-content-center align-items-center">
        <div className="spinner-border text-primary" role="status"></div>
      </div>
    );
  }

  return (
    <div className="min-vh-100 bg-light py-5">
      <Container className="max-w-3xl bg-white p-5 rounded shadow-sm">
        <div className="d-flex justify-content-between align-items-center mb-4">
          <h2 className="fw-bold text-primary mb-0">📝 完善您的個人履歷</h2>
          <button onClick={() => router.push("/")} className="btn btn-outline-secondary btn-sm">
            返回首頁
          </button>
        </div>
        
        <p className="text-muted mb-4">
          請填寫以下資訊。AI 面試官將會根據您的專業技能與經歷，為您量身打造專屬的面試情境！
        </p>

        <form onSubmit={handleSubmit}>
          <div className="mb-3">
            <label className="form-label fw-bold">1. 姓名 (Full Name)</label>
            <input
              type="text"
              className="form-control"
              placeholder="請輸入您的真實姓名或暱稱"
              value={formData.fullName}
              onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
              required
            />
          </div>

          <div className="mb-3">
            <label className="form-label fw-bold">2. 個人簡介 (Summary)</label>
            <textarea
              className="form-control"
              rows={3}
              placeholder="用 3-5 句話簡短介紹您自己、您的熱情以及職涯目標。"
              value={formData.summary}
              onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
              required
            ></textarea>
          </div>

          <div className="mb-3">
            <label className="form-label fw-bold">3. 專業技能 (Skills)</label>
            <textarea
              className="form-control"
              rows={3}
              placeholder="列出您的硬實力與軟實力（例如：Python, React, 專案管理, 資料庫設計...）"
              value={formData.skills}
              onChange={(e) => setFormData({ ...formData, skills: e.target.value })}
              required
            ></textarea>
          </div>

          <div className="mb-4">
            <label className="form-label fw-bold">4. 工作/專案經歷 (Experience)</label>
            <textarea
              className="form-control"
              rows={5}
              placeholder="請描述您過去的職位、參與過的專案，以及達成的具體成就。"
              value={formData.experience}
              onChange={(e) => setFormData({ ...formData, experience: e.target.value })}
              required
            ></textarea>
          </div>

          <button
            type="submit"
            className="btn btn-primary w-100 py-2 fw-bold"
            disabled={loading}
          >
            {loading ? "💾 儲存中並呼叫 AI 健檢..." : "💾 儲存履歷並獲取 AI 健檢建議"}
          </button>
        </form>

        {/* 顯示 Gemini 履歷健檢結果 */}
        {suggestion && (
          <div className="mt-5 p-4 bg-primary-subtle border border-primary rounded">
            <h5 className="fw-bold text-primary mb-3">✨ AI 履歷健檢報告</h5>
            <div style={{ whiteSpace: "pre-wrap", lineHeight: "1.6" }} className="text-dark">
              {suggestion}
            </div>
          </div>
        )}
      </Container>
    </div>
  );
}