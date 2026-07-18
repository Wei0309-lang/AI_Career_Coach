"use client";
// app/template.tsx — 全域頁面轉場
// Next.js 會在「每次路由切換」時重新掛載 template,
// 因此掛在這裡的進場動畫,每個頁面進入時都會播放一次。
export default function Template({ children }: { children: React.ReactNode }) {
  return <div className="page-enter">{children}</div>;
}