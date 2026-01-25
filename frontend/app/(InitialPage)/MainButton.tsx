import Image from "next/image";
import Link from "next/link";
export default function MainButton() {

      const features = [
    { name: "AI模擬面試", href: "/chat", description: "與 AI 職涯教練進行對話，獲取職涯建議。", color:"blue" , img:"/InitialPageImg/AiInterview.png"  },
    { name: "履歷健檢", href: "/check", description: "完成職涯測評，了解自己的職業傾向。", color:"green" , img:"/InitialPageImg/AiResume.png" },
    { name: "職涯探索", href: "/resources", description: "獲取個性化的職涯資源推薦。", color:"red", img:"/InitialPageImg/AiCareer.jpg" },
  ];

  const colorMap = {
    blue:{text: "text-blue-600", border: "border-blue-500"},
    green:{text: "text-green-600", border: "border-green-500"},
    red:{text: "text-red-600", border: "border-red-500"},
  }

    return (
        
    <div className="mt-30 grid gap-8  md:grid-cols-3 max-w-6xl mx-auto">
        {features.map((feature) => (
          <Link
            key={feature.name}
            href={feature.href}
            className={`text-center min-h-[320px] max-w-[500px] block p-6 rounded-lg shadow-lg hover:shadow-xl transition bg-white border-t-4 border-${feature.color}-500`}
          >
            <h2 className={`text-2xl font-semibold mb-4 text-${feature.color}-600` }>
              {feature.name}
            </h2>
            <p className="text-gray-700">{feature.description}</p>
            <Image
              src={feature.img}
              alt={feature.name} 
              width={500}
              height={500}
              className="object-contain h-48 w-full"/>
          </Link>
        ))}
      </div>
    );
}