import Spinner from 'react-bootstrap/Spinner'; // 引入 Bootstrap 的載入轉圈圈

interface ChatContent {
  role: "user" | "Ai";
  content: string;
}

interface ChatBodyProps {
  chatContents: ChatContent[];
  loading: boolean;
}

export default function ChatBody({ chatContents, loading }: ChatBodyProps) {
  return (
    // 1. flex-grow-1: 填滿剩餘空間 (取代 flex-1)
    // 2. overflow-auto: 內容太多時出現卷軸 (取代 overflow-y-auto)
    // 3. mb-5: 底部留白 (取代 mb-24，Bootstrap 預設最大只到 5，若不夠可用 style)
    <div className="flex-grow-1 overflow-auto px-3 pb-5" style={{ marginBottom: '4rem' }}>
      
      {chatContents.map((msg, i) => (
        <div
          key={i}
          // 4. d-flex: 啟用 Flexbox 以便控制排列
          // 5. justify-content-end/start: 控制左右對齊 (取代 text-right/left)
          // 6. mb-3: 訊息之間的間距 (取代 space-y-3)
          className={`d-flex mb-3 ${msg.role === "user" ? "justify-content-end" : "justify-content-start"}`}
        >
          {/* 訊息泡泡本體 */}
          <span 
            className={`
              d-inline-block p-3 rounded-3 
              ${msg.role === "user" ? "bg-primary text-white" : "bg-secondary text-white"}
            `}
            style={{ maxWidth: '75%' }} // 避免訊息太長時貼到邊邊
          >
            {msg.content}
          </span>
        </div>
      ))}

      {/* 載入狀態：改用 Bootstrap 的 Spinner 元件比較漂亮 */}
      {loading && (
        <div className="text-center text-muted mt-3">
          <Spinner animation="border" size="sm" role="status" className="me-2" />
          AI 思考中...
        </div>
      )}
    </div>
  );
}
