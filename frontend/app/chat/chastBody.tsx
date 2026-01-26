export default function ChatBody() {

interface ChatContent{
    
    role: "user" | "Ai" ;
    content: string;
}


  return (
    <div className="flex  p-6 overflow-y-auto">
      {/* 這裡是聊天內容區域 */}


      <label className="block mb-2 text-lg font-medium text-white">
        歡迎來到 AI 職涯教練平台！請在下方輸入您的問題或需求，我們的 AI 教練將竭誠為您提供專業的職涯建議與指導。無論是履歷撰寫、面試技巧還是職涯規劃，我們都能助您一臂之力。期待與您一同開啟成功的職涯旅程！
      </label>
    </div>
  );
}