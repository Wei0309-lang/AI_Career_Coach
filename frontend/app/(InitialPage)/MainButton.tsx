"use client";
// MainButton.tsx — 兩張功能卡片(深色玻璃面板風格)
// 路由邏輯與原版完全相同,僅調整外觀。
import React from "react";
import { useRouter } from "next/navigation";

export default function MainButton() {
  const router = useRouter();

  return (
    <div
      className="d-flex flex-column flex-md-row justify-content-center gap-4 mx-auto px-3"
      style={{ maxWidth: "880px" }}
    >

      {/* 第一張卡片:AI 模擬面試 */}
      <div className="studio-panel feature-card flex-fill p-4 text-center">
        <div className="icon-chip mb-3" aria-hidden="true">🎙️</div>
        <h4 className="studio-title fs-5 mb-2">AI 模擬面試</h4>
        <p className="studio-dim small mb-4">
          由資深技術面試官進行拷問，深度評估您的底層原理實力。
        </p>
        <button
          onClick={() => router.push("/chat")}
          className="btn btn-studio w-100"
        >
          進入面試室
        </button>
      </div>

      {/* 第二張卡片:履歷健檢 */}
      <div className="studio-panel feature-card flex-fill p-4 text-center">
        <div className="icon-chip icon-chip--teal mb-3" aria-hidden="true">📄</div>
        <h4 className="studio-title fs-5 mb-2">履歷健檢</h4>
        <p className="studio-dim small mb-4">
          填寫或更新您的個人經歷，獲取 Gemini 提供的專業修改建議。
        </p>
        <button
          onClick={() => router.push("/resume")}
          className="btn btn-studio-ghost w-100"
        >
          進入履歷健檢
        </button>
      </div>

      {/* 第三張卡片:面試歷史紀錄 */}
      <div className="studio-panel feature-card flex-fill p-4 text-center">
        <div className="icon-chip mb-3" style={{ background: "rgba(255, 180, 84, 0.12)", color: "#FFB454" }} aria-hidden="true">📊</div>
        <h4 className="studio-title fs-5 mb-2">面試歷史紀錄</h4>
        <p className="studio-dim small mb-4">
          回顧每一場面試的評分與建議，追蹤自己的進步軌跡。
        </p>
        <button
          onClick={() => router.push("/records")}
          className="btn btn-studio-ghost w-100"
        >
          查看歷史紀錄
        </button>
      </div>

    </div>

    
  );
}
