"use client";
import React from "react";
import { useRouter } from "next/navigation"; // 🌟 新增：引入路由套件

export default function MainButton() {
  const router = useRouter(); // 🌟 新增：初始化路由

  return (
    <div className="d-flex flex-column flex-md-row justify-content-center gap-4 max-w-4xl mx-auto px-3">
      
      {/* 第一個按鈕：AI 模擬面試 */}
      <div className="card shadow-sm border-0 flex-fill bg-white p-4 text-center rounded-4">
        <div className="fs-1 mb-2">🤖</div>
        <h4 className="fw-bold text-dark">AI 模擬面試</h4>
        <p className="text-muted small mb-4">由資深技術面試官進行拷問，深度評估您的底層原理實力。</p>
        <button 
          onClick={() => router.push("/chat")} 
          className="btn btn-primary fw-bold w-100 py-2 rounded-3"
        >
          開始模擬面試
        </button>
      </div>

      {/* 🌟 第二個按鈕：履歷健檢（完美整合處） */}
      <div className="card shadow-sm border-0 flex-fill bg-white p-4 text-center rounded-4 border border-primary-subtle">
        <div className="fs-1 mb-2">📝</div>
        <h4 className="fw-bold text-dark">履歷健檢</h4>
        <p className="text-muted small mb-4">填寫或更新您的個人經歷，獲取 Gemini 提供的專業修改建議。</p>
        <button 
          onClick={() => router.push("/resume")} 
          className="btn btn-outline-primary fw-bold w-100 py-2 rounded-3"
        >
          進入履歷健檢
        </button>
      </div>

    </div>
  );
}