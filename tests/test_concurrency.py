# 併發：解析履歷(同步阻塞的 PDF/Word 解析 + Gemini 呼叫)期間，其他請求不能被卡住。
# 這必須起一個真的 uvicorn 伺服器才測得出來(TestClient 不會重現 event loop 被阻塞的情況)。
import threading
import time

import httpx
import pytest
import uvicorn

import Main

AI_DELAY_SECONDS = 2.0


@pytest.fixture
def live_server():
    config = uvicorn.Config(Main.app, host="127.0.0.1", port=0, log_level="error", ws="none")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    assert server.started, "uvicorn 沒有在 10 秒內啟動"
    port = server.servers[0].sockets[0].getsockname()[1]
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)


def test_resume_parsing_does_not_block_other_requests(live_server, login, fake_gemini, monkeypatch):
    """修正前 /api/resume/parse 是 async def 卻呼叫同步的 Gemini，解析期間 GET / 要等 2.5 秒以上。"""
    from test_resume import docx_bytes, table_resume

    login("u1")
    fake_gemini.reply = '{"fullName": "王小明", "summary": "", "skills": "", "experience": ""}'
    slow_generate = fake_gemini.generate_content

    def slow(*args, **kwargs):
        time.sleep(AI_DELAY_SECONDS)
        return slow_generate(*args, **kwargs)

    monkeypatch.setattr(fake_gemini, "generate_content", slow)
    parse_result = {}

    def do_parse():
        parse_result["status"] = httpx.post(
            f"{live_server}/api/resume/parse",
            files={"file": ("cv.docx", docx_bytes(table_resume), "application/octet-stream")},
            timeout=30,
        ).status_code

    parser = threading.Thread(target=do_parse)
    parser.start()
    time.sleep(0.5)  # 確定解析請求已經在等「Gemini」

    started = time.time()
    assert httpx.get(f"{live_server}/", timeout=30).status_code == 200
    other_request_latency = time.time() - started
    parser.join()

    assert parse_result["status"] == 200
    assert other_request_latency < 0.5, f"解析期間其他請求等了 {other_request_latency:.2f} 秒"
