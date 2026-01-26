from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
import asyncio


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["http://localhost:3000"],
    allow_methods = ["*"],
    allow_headers=["*"],)

fakeResponses = "This is a fake response."


@app.get("/")
async def root():
    return {"message": "Hello World"}

async def get_response_from_ai(message: str) -> str:
    await asyncio.sleep(2)  # 模擬延遲
    return f"AI 回覆: {message}"

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0" , port=8001)  