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
    <div className="flex-1 overflow-y-auto space-y-3 mb-24">
      {chatContents.map((msg, i) => (
        <div
          key={i}
          className={msg.role === "user" ? "text-right" : "text-left"}
        >
          <span className="inline-block bg-gray-500 text-white p-3 rounded-lg">
            {msg.content}
          </span>
        </div>
      ))}

      {loading && <div className="text-gray-300">AI 思考中...</div>}
    </div>
  );
}
