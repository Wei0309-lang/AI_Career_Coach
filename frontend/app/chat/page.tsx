"use client";

import { useState } from "react";
import InputBox from "./InputBox";
import ChatBody from "./chastBody";

export default function Home() {


const [message, setMessage] = useState<string>("等待連線中...")

const UserSend = (InputWebText:string) => {
  console.log("收到訊息:", InputWebText);

  setMessage(InputWebText);
}


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
    <div className="min-h-screen flex flex-col bg-gray-700 left-15 p-10">
      {/* 顯示標題 */}
      <h1 className=" flex text-4xl left-15 font-bold mb-6 text-gray-400">
        AI 職涯教練平台
      </h1>
      
     
      
      <ChatBody/>
      <InputBox onSend={UserSend}/>
      
    </div>

  );
}