"use client";
import { useState } from "react";

interface InputBoxProps {
    onSend: (message: string) => void;

}

export default function InputBox({onSend}: InputBoxProps) {

    const [input, setInput] = useState(""); {/* 輸入框的狀態 */}

    const handleKeyDown = (e:React.KeyboardEvent) => { {/* 按下Enter鍵送出 */}
        if(e.key === 'Enter'){

            if(e.nativeEvent.isComposing) {   
                return;
            }
            
            e.preventDefault();

            handleSend();
        }
    }


    const handleSend = () => { {/* 空白例外處理、傳送、重設input */}

        if(input.trim() === ""){
            return;
        }

        if(onSend && input.trim() !== ""){
            onSend(input.trim());
            setInput("");
        }
    }

  return (
    <div className="fixed bottom-0 right-0 w-[1300px] p-4 rounded rounded-lg rounded-xl  border-gray-800 bg-gray-600  ">
      <input
        type="text"
        placeholder="輸入您的訊息..."
        className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}

      />
    </div>
  );
}