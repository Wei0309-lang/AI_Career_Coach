"use client";

import { useState } from "react";
export default function Home() {
  const [message, setMessage] = useState("等待連線中...")


const callBackend = async () => {
  try {
    const response = await fetch("http://localhost:8001/");
    const data = await response.json();
    setMessage(data.message);
  } catch (error) {
    setMessage("無法連接到後端服務器");
  }
}
return (
    <div>
      {/* 顯示標題 */}
      <h1 className="text-4xl font-bold mb-6 text-blue-600">
        AI 職涯教練平台
      </h1>
      
      {/* 顯示按鈕 */}
      <button onClick={callBackend} className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition shadow-lg" >
        呼叫後端 API
      </button>

      {/* 顯示變數 */}
      <div className="mt-8 p-4 border border-gray-300 rounded-md bg-white">
        <p className="text-xl">
          後端回應：
          <span className="font-bold text-green-600 ml-2">
            {message}
          </span>
        </p>
      </div>
    </div>
  );
}