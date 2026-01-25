import Link from "next/link";
import Header from "./Header";
import MainButton from "./MainButton";

export default function Dashboard() {


  return (
    <>
    
    <Header />
    <div className="min-h-screen bg-slate-100 px-6 py-15">
      <h1 className="text-7xl font-bold text-center text-blue-600">
        您的AI職涯導師
      </h1>
      <h2 className="text-3xl text-center text-gray-700 mt-4">
        探索我們的功能，開始您的職涯旅程！
      </h2>  
      <MainButton />

    </div>
    </>
  )
}

