"use client";
// chat/page.tsx — 面試室 v2:選擇模式 → 場次面試 → 結束領取報告
// 流程:setup(選職位/難度)→ interview(對話,3D 虛擬人開口)→ report(AI 評估報告)
// HeyGen 模式不走場次流程(iframe 自帶對話),維持原本行為。

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import InputBox from "./InputBox";
import ChatBody from "./chatBody"; // 注意：請確認您的檔案名稱大小寫是否正確
import Container from 'react-bootstrap/Container';
import AuthGuard from "../components/AuthGuard";
import { BACKEND_URL, authHeaders, ApiError, apiError } from "../lib/api";
import type { AvatarMessage } from "./Avatar3D";

const Avatar3D = dynamic(() => import("./Avatar3D"), { ssr: false });
const HeyGenAvatar = dynamic(() => import("./HeyGenAvatar"), { ssr: false });

const AVATAR_MODE = process.env.NEXT_PUBLIC_AVATAR_MODE; // "3d" | "heygen" | undefined
const AVATAR_3D_ENABLED = AVATAR_MODE === "3d";

const POSITIONS = ["前端工程師", "後端工程師", "資安工程師", "全端工程師"];
const LEVELS = ["實習生", "新鮮人", "資深工程師"];

interface ChatContent {
    role: "user" | "Ai";
    content: string;
}

interface Report {
    overall_score: number;
    dimensions: {
        technical: { score: number; comment: string };
        communication: { score: number; comment: string };
        problem_solving: { score: number; comment: string };
    };
    strengths: string[];
    improvements: string[];
    summary: string;
}

// 尚未按「結束」的場次(例如面試到一半重新整理頁面)，由 /api/interview/active 取得
interface ActiveSession {
    session_id: string;
    position: string;
    level: string;
    date: string;
    messages: { role: string; content: string }[];
}

function ChatPageContent() {
    const router = useRouter();
    const [chatContents, setChatContents] = useState<ChatContent[]>([]);
    const [loading, setLoading] = useState(false);
    const [avatarMsg, setAvatarMsg] = useState<AvatarMessage | null>(null);

    // 面試場次流程狀態
    const [stage, setStage] = useState<"setup" | "interview" | "report">("setup");
    const [position, setPosition] = useState<string>("");
    const [level, setLevel] = useState<string>("");
    const [sessionId, setSessionId] = useState<string>("");
    const [report, setReport] = useState<Report | null>(null);
    const [finishing, setFinishing] = useState(false);
    const [activeSession, setActiveSession] = useState<ActiveSession | null>(null);

    // 進入頁面時檢查是否有未結束的場次，有的話在設定畫面提供「繼續面試」
    useEffect(() => {
        if (AVATAR_MODE === "heygen") return;
        let cancelled = false;
        (async () => {
            try {
                const res = await fetch(`${BACKEND_URL}/api/interview/active`, {
                    headers: await authHeaders(),
                });
                if (!res.ok) return;
                const data = await res.json();
                if (!cancelled && data.session) setActiveSession(data.session);
            } catch (e) {
                console.error("讀取進行中的面試失敗:", e);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, []);

    // 接回未結束的場次：還原對話紀錄，直接回到面試畫面
    const handleResume = () => {
        if (!activeSession) return;
        setSessionId(activeSession.session_id);
        setPosition(activeSession.position);
        setLevel(activeSession.level);
        setChatContents(activeSession.messages.map(m => ({
            role: m.role === "user" ? "user" : "Ai",
            content: m.content,
        })));
        setActiveSession(null);
        setStage("interview");
    };

    // 開始面試:建立場次,取得面試官開場白
    const handleStart = async () => {
        if (!position || !level) return;
        setLoading(true);
        try {
            const res = await fetch(`${BACKEND_URL}/api/interview/start`, {
                method: "POST",
                headers: await authHeaders(true),
                body: JSON.stringify({ position, level }),
            });
            if (!res.ok) throw await apiError(res, "無法開始面試，請稍後再試一次。");
            const data = await res.json();
            setSessionId(data.session_id);
            setActiveSession(null); // 後端開新場次時已把舊的未結束場次標記為放棄
            setChatContents([{ role: "Ai", content: data.opening }]);
            if (AVATAR_3D_ENABLED) {
                setAvatarMsg({ id: Date.now(), text: data.opening });
            }
            setStage("interview");
        } catch (e) {
            console.error("開始面試失敗:", e);
            alert(e instanceof ApiError ? e.message : "無法開始面試,請確認後端服務正常後再試一次。");
        } finally {
            setLoading(false);
        }
    };

    // 場次內對話
    const handleSend = async (text: string) => {
        // 上一則還在等面試官回覆、或正在產生報告時不接受新訊息
        if (loading || finishing) return;
        setChatContents(prev => [...prev, { role: "user", content: text }]);
        setLoading(true);
        try {
            const res = await fetch(`${BACKEND_URL}/api/interview/chat`, {
                method: "POST",
                headers: await authHeaders(true),
                body: JSON.stringify({ session_id: sessionId, message: text }),
            });
            if (!res.ok) throw await apiError(res, "面試官暫時忙線中，請稍後再試一次。");
            const data = await res.json();
            setChatContents(prev => [...prev, { role: "Ai", content: data.response }]);
            if (AVATAR_3D_ENABLED) {
                setAvatarMsg({ id: Date.now(), text: data.response });
            }
        } catch (error) {
            console.error("連線錯誤:", error);
            setChatContents(prev => [
                ...prev,
                {
                    role: "Ai",
                    content: error instanceof ApiError ? `（系統訊息）${error.message}` : "面試官暫時忙線中，請稍後再試一次。",
                },
            ]);
        } finally {
            setLoading(false);
        }
    };

    // 結束面試 → 生成報告
    const handleFinish = async () => {
        if (!sessionId) return;
        setFinishing(true);
        try {
            const res = await fetch(`${BACKEND_URL}/api/interview/finish`, {
                method: "POST",
                headers: await authHeaders(true),
                body: JSON.stringify({ session_id: sessionId }),
            });
            const data = await res.json();
            if (!res.ok) {
                alert(data.detail || "產生報告失敗,請再試一次");
                return;
            }
            setReport(data.report);
            setStage("report");
        } catch (e) {
            console.error("結束面試失敗:", e);
            alert("產生報告失敗,請再試一次");
        } finally {
            setFinishing(false);
        }
    };

    // 重新開始
    const handleRestart = () => {
        setStage("setup");
        setSessionId("");
        setChatContents([]);
        setReport(null);
        setPosition("");
        setLevel("");
    };

    // ---------- HeyGen 模式:維持原本純 iframe 體驗 ----------
    if (AVATAR_MODE === "heygen") {
        return (
            <div className="studio-bg d-flex flex-column">
                <Container className="px-4 pt-4 flex-grow-1 d-flex flex-column">
                    <div className="d-flex align-items-center justify-content-between mb-4">
                        <div>
                            <span className="studio-eyebrow">Mock Interview</span>
                            <h1 className="studio-title fs-3 mb-0">AI 模擬面試室</h1>
                        </div>
                        <span className="onair">面試進行中</span>
                    </div>
                    <div className="mx-auto w-100" style={{ maxWidth: "960px" }}>
                        <HeyGenAvatar />
                        <div className="text-center mt-2">
                            <span className="studio-dim small">林經理 · 資深技術面試官（擬真模式）</span>
                        </div>
                    </div>
                </Container>
            </div>
        );
    }

    return (
        <div className="studio-bg d-flex flex-column">
            <Container
                className="px-4 pt-4 flex-grow-1 d-flex flex-column"
                style={{ paddingBottom: stage === "interview" ? "110px" : "40px" }}
            >
                {/* 頁首 */}
                <div className="d-flex align-items-center justify-content-between mb-4">
                    <div>
                        <span className="studio-eyebrow">Mock Interview</span>
                        <h1 className="studio-title fs-3 mb-0">AI 模擬面試室</h1>
                    </div>
                    {stage === "interview" && (
                        <div className="d-flex align-items-center gap-3">
                            <span className="onair">面試進行中</span>
                            <button
                                className="btn btn-studio-ghost btn-sm px-3"
                                onClick={handleFinish}
                                disabled={finishing || loading}
                            >
                                {finishing ? "評估中..." : "結束面試並取得報告"}
                            </button>
                        </div>
                    )}
                </div>

                {/* ---------- 階段一:面試設定 ---------- */}
                {stage === "setup" && (
                    <div className="studio-panel p-4 p-md-5 mx-auto w-100" style={{ maxWidth: "640px" }}>
                        <h5 className="studio-title mb-1">設定本場面試</h5>
                        <p className="studio-dim small mb-4">面試官會根據目標職位與級別調整提問方向與評估標準</p>

                        {activeSession && (
                            <div
                                className="mb-4 p-3 rounded-3"
                                style={{ background: "rgba(108, 140, 255, 0.08)", border: "1px solid rgba(108, 140, 255, 0.3)" }}
                            >
                                <p className="small mb-1" style={{ color: "var(--studio-accent)", fontWeight: 700 }}>
                                    您有一場尚未結束的面試
                                </p>
                                <p className="studio-dim small mb-3">
                                    {activeSession.position}（{activeSession.level}）· 開始於 {activeSession.date}。
                                    若直接開始新面試，這一場將視為放棄，不會產生報告。
                                </p>
                                <button className="btn btn-studio btn-sm px-4" onClick={handleResume}>
                                    繼續這場面試
                                </button>
                            </div>
                        )}

                        <p className="studio-dim small mb-2">目標職位</p>
                        <div className="d-flex flex-wrap gap-2 mb-4">
                            {POSITIONS.map(p => (
                                <button key={p}
                                    className={`btn btn-sm rounded-pill px-3 ${position === p ? "btn-studio" : "btn-studio-ghost"}`}
                                    onClick={() => setPosition(p)}>
                                    {p}
                                </button>
                            ))}
                        </div>

                        <p className="studio-dim small mb-2">應徵級別</p>
                        <div className="d-flex flex-wrap gap-2 mb-4">
                            {LEVELS.map(l => (
                                <button key={l}
                                    className={`btn btn-sm rounded-pill px-3 ${level === l ? "btn-studio" : "btn-studio-ghost"}`}
                                    onClick={() => setLevel(l)}>
                                    {l}
                                </button>
                            ))}
                        </div>

                        <button
                            className="btn btn-studio w-100"
                            disabled={!position || !level || loading}
                            onClick={handleStart}
                        >
                            {loading ? "面試官入場中..." : "開始面試"}
                        </button>
                    </div>
                )}

                {/* ---------- 階段二:面試進行 ---------- */}
                {stage === "interview" && (
                    <>
                        {AVATAR_MODE === "3d" && (
                            <div className="studio-tile mx-auto w-100" style={{ maxWidth: "820px" }}>
                                <Avatar3D message={avatarMsg} />
                                <div className="studio-nametag2">
                                    <div>
                                        <span className="name">林經理</span>
                                        <span className="role">資深技術面試官</span>
                                    </div>
                                    <div className="chips">
                                        <span className="chip">{position}</span>
                                        <span className="chip chip--level">{level}</span>
                                    </div>
                                </div>
                            </div>
                        )}
                        <ChatBody chatContents={chatContents} loading={loading} />
                    </>
                )}

                {/* ---------- 階段三:面試報告 ---------- */}
                {stage === "report" && report && (
                    <div className="studio-panel p-4 p-md-5 mx-auto w-100" style={{ maxWidth: "720px" }}>
                        <div className="text-center mb-4">
                            <span className="studio-eyebrow">Interview Report</span>
                            <h4 className="studio-title mt-1">面試評估報告</h4>
                            <p className="studio-dim small">{position}（{level}）</p>
                            <div className="studio-title" style={{ fontSize: "3.5rem", color: "var(--studio-accent)" }}>
                                {report.overall_score}
                                <span className="fs-6 studio-dim"> / 100</span>
                            </div>
                        </div>

                        {([
                            ["技術深度", report.dimensions.technical],
                            ["溝通表達", report.dimensions.communication],
                            ["問題解決", report.dimensions.problem_solving],
                        ] as [string, { score: number; comment: string }][]).map(([label, d]) => (
                            <div key={label} className="mb-3">
                                <div className="d-flex justify-content-between small mb-1">
                                    <span>{label}</span>
                                    <span className="studio-dim">{d.score} / 10</span>
                                </div>
                                <div style={{ height: 8, borderRadius: 4, background: "rgba(255,255,255,.08)" }}>
                                    <div style={{
                                        width: `${d.score * 10}%`, height: "100%", borderRadius: 4,
                                        background: "linear-gradient(90deg, #6C8CFF, #22D3B6)",
                                    }} />
                                </div>
                                <p className="studio-dim small mt-1 mb-0">{d.comment}</p>
                            </div>
                        ))}

                        <hr style={{ borderColor: "var(--studio-line)" }} />

                        <p className="small mb-1" style={{ color: "var(--studio-accent-2)" }}>表現亮點</p>
                        {report.strengths.map((s, i) => (
                            <p key={i} className="small mb-1">・{s}</p>
                        ))}

                        <p className="small mb-1 mt-3" style={{ color: "#FFB454" }}>改進建議</p>
                        {report.improvements.map((s, i) => (
                            <p key={i} className="small mb-1">・{s}</p>
                        ))}

                        <p className="studio-dim small mt-3">{report.summary}</p>

                        <div className="d-flex gap-2 mt-4">
                            <button className="btn btn-studio flex-fill" onClick={handleRestart}>
                                再面試一次
                            </button>
                            <button className="btn btn-studio-ghost flex-fill" onClick={() => router.push("/records")}>
                                查看歷史紀錄
                            </button>
                        </div>
                    </div>
                )}

            </Container>

            {stage === "interview" && <InputBox onSend={handleSend} disabled={loading || finishing} />}
        </div>
    );
}

export default function Home() {
    return (
        <AuthGuard
            fallback={
                <div className="studio-bg d-flex justify-content-center align-items-center">
                    <div className="studio-dim">安全性驗證中...</div>
                </div>
            }
        >
            <ChatPageContent />
        </AuthGuard>
    );
}
