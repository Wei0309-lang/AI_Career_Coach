# 面試場次流程：開始 / 對話 / 結束報告 / 接回場次 / 歷史紀錄
import json
from datetime import datetime, timedelta

import pytest

import Model
import interview
from conftest import VALID_REPORT_JSON

START = {"position": "後端工程師", "level": "新鮮人"}


def start(client, fake_ai, opening="您好，請先自我介紹。"):
    fake_ai.replies.append(opening)
    r = client.post("/api/interview/start", json=START)
    assert r.status_code == 200, r.text
    return r.json()["session_id"]


def answer(client, session_id, message="我的回答"):
    return client.post("/api/interview/chat", json={"session_id": session_id, "message": message})


# ---------- 開始與對話 ----------
def test_start_returns_opening_and_saves_it(client, login, fake_ai, db):
    login("u1")
    sid = start(client, fake_ai, opening="我是林經理，請自我介紹。")
    msgs = db.query(Model.ChatMessage).filter_by(session_id=sid).all()
    assert [(m.role, m.content) for m in msgs] == [("assistant", "我是林經理，請自我介紹。")]


def test_start_rejects_unknown_position(client, login, fake_ai):
    login("u1")
    r = client.post("/api/interview/start", json={"position": "廚師", "level": "新鮮人"})
    assert r.status_code == 400


def test_start_falls_back_to_default_opening_when_ai_fails(client, login, fake_ai):
    login("u1")
    fake_ai.replies.append(RuntimeError("AI down"))
    r = client.post("/api/interview/start", json=START)
    assert r.status_code == 200
    assert "林經理" in r.json()["opening"]


def test_chat_uses_most_recent_20_messages_in_order(client, login, fake_ai, db):
    """修正前用正序 limit(20)，面試超過 10 輪後面試官只看得到最舊的對話。"""
    login("u1")
    sid = start(client, fake_ai)
    base = datetime.utcnow() + timedelta(minutes=1)
    for i in range(30):
        db.add(Model.ChatMessage(user_id="u1", session_id=sid, role="user" if i % 2 == 0 else "assistant",
                                 content=f"MSG{i:02d}", created_at=base + timedelta(seconds=i)))
    db.commit()

    assert answer(client, sid, "最新的回答").status_code == 200
    prompt = fake_ai.calls[-1]["prompt"]
    assert "MSG29" in prompt and "MSG10" in prompt
    assert "MSG09" not in prompt and "MSG00" not in prompt
    assert prompt.index("MSG10") < prompt.index("MSG29") < prompt.index("最新的回答")


def test_cannot_chat_in_someone_elses_session(client, login, fake_ai):
    login("u1")
    sid = start(client, fake_ai)
    login("u2")
    assert answer(client, sid).status_code == 404


# ---------- 報告 ----------
def finish_with(client, login, fake_ai, *report_replies):
    login("u1")
    sid = start(client, fake_ai)
    answer(client, sid)
    fake_ai.replies.extend(report_replies)
    return sid, client.post("/api/interview/finish", json={"session_id": sid})


def test_finish_requests_json_with_report_system_prompt(client, login, fake_ai):
    sid, r = finish_with(client, login, fake_ai, VALID_REPORT_JSON)
    assert r.status_code == 200
    assert r.json()["report"]["overall_score"] == 72
    call = fake_ai.calls[-1]
    assert call["json_mode"] is True and call["system"] == interview.REPORT_SYSTEM_PROMPT


def test_finish_retries_once_when_first_output_is_truncated(client, login, fake_ai):
    """本地 Llama 3 常漏掉最後一個 }，重試一次通常就會成功。"""
    truncated = VALID_REPORT_JSON[:-1]
    sid, r = finish_with(client, login, fake_ai, truncated, VALID_REPORT_JSON)
    assert r.status_code == 200
    assert r.json()["report"]["overall_score"] == 72


def test_finish_returns_502_and_keeps_session_active_when_output_is_never_a_report(client, login, fake_ai, db):
    sid, r = finish_with(client, login, fake_ai, "我是面試官，請問你還有問題嗎？", "{}")
    assert r.status_code == 502
    assert db.get(Model.InterviewSession, sid).status == "active"


def test_finish_rejects_too_short_interview(client, login, fake_ai):
    login("u1")
    sid = start(client, fake_ai)
    r = client.post("/api/interview/finish", json={"session_id": sid})
    assert r.status_code == 400


def test_finishing_twice_returns_same_report_without_calling_ai_again(client, login, fake_ai):
    sid, first = finish_with(client, login, fake_ai, VALID_REPORT_JSON)
    json_calls = sum(c["json_mode"] for c in fake_ai.calls)
    second = client.post("/api/interview/finish", json={"session_id": sid})
    assert second.status_code == 200 and second.json() == first.json()
    assert sum(c["json_mode"] for c in fake_ai.calls) == json_calls


@pytest.mark.parametrize("raw, expected", [
    # 型別錯誤、缺欄位、超出範圍都要補齊/校正，前端才不會因為讀不到 dimensions.* 而白屏
    ('{"overall_score": "85分", "dimensions": {"technical": {"score": "8/10"}, "communication": "很好"}}',
     {"overall": 85, "technical": 8, "communication": 0, "problem_solving": 0}),
    ('{"overall_score": 150, "dimensions": {"technical": {"score": 12}}}',
     {"overall": 100, "technical": 10, "communication": 0, "problem_solving": 0}),
    ('```json\n{"overall_score": 7.6, "dimensions": {}}\n```',
     {"overall": 8, "technical": 0, "communication": 0, "problem_solving": 0}),
])
def test_parse_report_normalizes_messy_output(raw, expected):
    report = interview.parse_report(raw)
    assert report is not None
    data = report.model_dump()
    assert set(data) == {"overall_score", "dimensions", "strengths", "improvements", "summary"}
    assert data["overall_score"] == expected["overall"]
    for dim in ("technical", "communication", "problem_solving"):
        assert data["dimensions"][dim]["score"] == expected[dim]


def test_parse_report_turns_strings_and_objects_into_text_lists():
    report = interview.parse_report('{"overall_score": 60, "strengths": "表達清楚", "improvements": [{"點": "多舉例"}]}')
    assert report.strengths == ["表達清楚"] and report.improvements == ["多舉例"]


@pytest.mark.parametrize("raw", ["", "不是 JSON", "{}", '{"foo": 1}', "[1, 2]", '{"overall_score": 1'])
def test_parse_report_rejects_non_reports(raw):
    assert interview.parse_report(raw) is None


# ---------- 接回場次 / 放棄 ----------
def test_active_returns_unfinished_session_with_full_transcript(client, login, fake_ai):
    login("u1")
    assert client.get("/api/interview/active").json() == {"session": None}
    sid = start(client, fake_ai)
    answer(client, sid, "我的第一個回答")
    active = client.get("/api/interview/active").json()["session"]
    assert active["session_id"] == sid
    assert [m["role"] for m in active["messages"]] == ["assistant", "user", "assistant"]
    assert active["messages"][1]["content"] == "我的第一個回答"


def test_starting_new_interview_abandons_previous_one(client, login, fake_ai, db):
    login("u1")
    old = start(client, fake_ai)
    new = start(client, fake_ai)
    db.expire_all()
    assert db.get(Model.InterviewSession, old).status == "abandoned"
    assert client.get("/api/interview/active").json()["session"]["session_id"] == new
    assert answer(client, old).status_code == 400
    assert client.post("/api/interview/finish", json={"session_id": old}).status_code == 400


# ---------- 歷史紀錄 ----------
def test_history_lists_only_finished_sessions(client, login, fake_ai):
    sid, _ = finish_with(client, login, fake_ai, VALID_REPORT_JSON)
    start(client, fake_ai)  # 另一場進行中的面試不應出現在紀錄裡
    sessions = client.get("/api/interview/history").json()["sessions"]
    assert [s["session_id"] for s in sessions] == [sid]
    assert sessions[0]["overall_score"] == 72


def test_history_and_detail_show_taiwan_time(client, login, db):
    """資料庫存 UTC，顯示時要轉成台灣時間(UTC+8)。修正前會差 8 小時。"""
    login("u1")
    s = Model.InterviewSession(user_id="u1", position="前端工程師", level="實習生", status="finished",
                               report_json=json.dumps({"overall_score": 60}), created_at=datetime(2026, 9, 25, 16, 30))
    db.add(s)
    db.commit()
    assert client.get("/api/interview/history").json()["sessions"][0]["date"] == "2026-09-26 00:30"
    assert client.get(f"/api/interview/detail/{s.id}").json()["date"] == "2026-09-26 00:30"


def test_detail_fills_missing_fields_of_old_reports(client, login, db):
    login("u1")
    s = Model.InterviewSession(user_id="u1", position="前端工程師", level="實習生", status="finished",
                               report_json=json.dumps({"overall_score": 60, "summary": "舊資料"}))
    db.add(s)
    db.commit()
    report = client.get(f"/api/interview/detail/{s.id}").json()["report"]
    assert report["dimensions"]["technical"] == {"score": 0, "comment": ""}
    assert report["summary"] == "舊資料"
