"use client";
// app/records/page.tsx — 面試歷史紀錄 v2
// 點擊卡片展開完整評分報告(三維度進度條、亮點、建議、總評),可再展開面試逐字稿。
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Container from "react-bootstrap/Container";
import AuthGuard from "../components/AuthGuard";
import { supabase } from "../lib/supabaseClient";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

// 每次呼叫受保護的後端 API 前，即時取用 Supabase session 的 JWT
async function authHeaders(): Promise<Record<string, string>> {
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) {
    throw new Error("尚未登入");
  }
  return { "Authorization": `Bearer ${session.access_token}` };
}

interface SessionSummary {
  session_id: string;
  position: string;
  level: string;
  date: string;
  overall_score: number | null;
  summary: string;
}

interface Dimension { score: number; comment: string; }
interface Detail {
  position: string;
  level: string;
  date: string;
  report: {
    overall_score: number;
    dimensions: { technical: Dimension; communication: Dimension; problem_solving: Dimension };
    strengths: string[];
    improvements: string[];
    summary: string;
  } | null;
  transcript: { role: string; content: string }[];
}

function RecordsPageContent() {
  const router = useRouter();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);

  // 展開狀態:目前展開的 session_id、詳細資料快取、逐字稿開關
  const [openId, setOpenId] = useState<string>("");
  const [details, setDetails] = useState<Record<string, Detail>>({});
  const [detailLoading, setDetailLoading] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/interview/history`, {
          headers: await authHeaders(),
        });
        const d = await res.json();
        setSessions(d.sessions || []);
      } catch (e) {
        console.error("讀取紀錄失敗:", e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // 點擊卡片:展開/收合,首次展開時抓取詳細報告
  const toggleDetail = async (sessionId: string) => {
    setShowTranscript(false);
    if (openId === sessionId) {
      setOpenId("");
      return;
    }
    setOpenId(sessionId);
    if (!details[sessionId]) {
      setDetailLoading(true);
      try {
        const res = await fetch(
          `${BACKEND_URL}/api/interview/detail/${sessionId}`,
          { headers: await authHeaders() }
        );
        if (res.ok) {
          const d = await res.json();
          setDetails((prev) => ({ ...prev, [sessionId]: d }));
        }
      } catch (e) {
        console.error("讀取詳細報告失敗:", e);
      } finally {
        setDetailLoading(false);
      }
    }
  };

  return (
    <div className="studio-bg">
      <Container className="px-4 py-5" style={{ maxWidth: "860px" }}>
        <div className="d-flex align-items-center justify-content-between mb-4">
          <div>
            <span className="studio-eyebrow">Interview Records</span>
            <h1 className="studio-title fs-3 mb-0">面試歷史紀錄</h1>
          </div>
          <button className="btn btn-studio-ghost btn-sm px-3" onClick={() => router.push("/")}>
            返回首頁
          </button>
        </div>

        {loading && <p className="studio-dim">載入中...</p>}

        {!loading && sessions.length === 0 && (
          <div className="studio-panel p-5 text-center">
            <p className="studio-dim mb-3">還沒有完成任何面試</p>
            <button className="btn btn-studio px-4" onClick={() => router.push("/chat")}>
              開始第一場模擬面試
            </button>
          </div>
        )}

        {sessions.map((s) => {
          const isOpen = openId === s.session_id;
          const d = details[s.session_id];
          return (
            <div key={s.session_id} className="studio-panel mb-3" style={{ overflow: "hidden" }}>

              {/* ---- 卡片標頭(可點擊展開) ---- */}
              <div
                className="p-4 d-flex align-items-center gap-4"
                style={{ cursor: "pointer" }}
                onClick={() => toggleDetail(s.session_id)}
              >
                <div className="text-center flex-shrink-0" style={{ width: "84px" }}>
                  <div className="studio-title fs-3" style={{ color: "var(--studio-accent)" }}>
                    {s.overall_score ?? "--"}
                  </div>
                  <div className="studio-dim" style={{ fontSize: "0.7rem" }}>總分</div>
                </div>
                <div className="flex-grow-1">
                  <div className="d-flex align-items-baseline gap-2 mb-1">
                    <span className="studio-title">{s.position}</span>
                    <span className="studio-dim small">{s.level}</span>
                    <span className="studio-dim small ms-auto">{s.date}</span>
                  </div>
                  <p className="studio-dim small mb-0">{s.summary}</p>
                </div>
                <span className="studio-dim" style={{ fontSize: "1.1rem" }}>
                  {isOpen ? "▲" : "▼"}
                </span>
              </div>

              {/* ---- 展開:完整評分報告 ---- */}
              {isOpen && (
                <div className="px-4 pb-4" style={{ borderTop: "1px solid var(--studio-line)" }}>
                  {detailLoading && !d && (
                    <p className="studio-dim small pt-3 mb-0">載入詳細報告中...</p>
                  )}

                  {d?.report && (
                    <div className="pt-4">
                      {([
                        ["技術深度", d.report.dimensions.technical],
                        ["溝通表達", d.report.dimensions.communication],
                        ["問題解決", d.report.dimensions.problem_solving],
                      ] as [string, Dimension][]).map(([label, dim]) => (
                        <div key={label} className="mb-3">
                          <div className="d-flex justify-content-between small mb-1">
                            <span>{label}</span>
                            <span className="studio-dim">{dim.score} / 10</span>
                          </div>
                          <div style={{ height: 8, borderRadius: 4, background: "rgba(255,255,255,.08)" }}>
                            <div style={{
                              width: `${dim.score * 10}%`, height: "100%", borderRadius: 4,
                              background: "linear-gradient(90deg, #6C8CFF, #22D3B6)",
                            }} />
                          </div>
                          <p className="studio-dim small mt-1 mb-0">{dim.comment}</p>
                        </div>
                      ))}

                      <hr style={{ borderColor: "var(--studio-line)" }} />

                      <p className="small mb-1" style={{ color: "var(--studio-accent-2)" }}>表現亮點</p>
                      {d.report.strengths.map((t, i) => (
                        <p key={i} className="small mb-1">・{t}</p>
                      ))}

                      <p className="small mb-1 mt-3" style={{ color: "#FFB454" }}>改進建議</p>
                      {d.report.improvements.map((t, i) => (
                        <p key={i} className="small mb-1">・{t}</p>
                      ))}

                      <p className="studio-dim small mt-3">{d.report.summary}</p>

                      {/* ---- 逐字稿(預設收合) ---- */}
                      <button
                        className="btn btn-studio-ghost btn-sm px-3 mt-2"
                        onClick={(e) => { e.stopPropagation(); setShowTranscript(!showTranscript); }}
                      >
                        {showTranscript ? "收合面試逐字稿" : `查看面試逐字稿(${d.transcript.length} 則)`}
                      </button>

                      {showTranscript && (
                        <div className="mt-3 p-3 rounded-3"
                          style={{ background: "rgba(255,255,255,.03)", border: "1px solid var(--studio-line)", maxHeight: "340px", overflowY: "auto" }}>
                          {d.transcript.map((m, i) => (
                            <p key={i} className="small mb-2">
                              <span style={{ color: m.role === "user" ? "var(--studio-accent)" : "var(--studio-accent-2)", fontWeight: 700 }}>
                                {m.role === "user" ? "我" : "林經理"}：
                              </span>
                              {m.content}
                            </p>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </Container>
    </div>
  );
}

export default function RecordsPage() {
  return (
    <AuthGuard
      fallback={
        <div className="studio-bg d-flex justify-content-center align-items-center">
          <div className="studio-dim">安全性驗證中...</div>
        </div>
      }
    >
      <RecordsPageContent />
    </AuthGuard>
  );
}
