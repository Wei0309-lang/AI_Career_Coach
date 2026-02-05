// src/app/page.tsx (假設這是你的首頁)
import Link from "next/link";
import Container from 'react-bootstrap/Container'; // 引入容器
import Header from "./Header";
import MainButton from "./MainButton";

export default function Dashboard() {
  return (
    <>
      <Header />
      {/*  min-vh-100 (最小高度 100% 視窗)
         2. bg-light ( 淺灰背景)
         3.  py-5 (Bootstrap 間距最大通常到 5)
      */}
      <div className="min-vh-100 bg-primary-subtle px-4 py-5 ">
        <Container>
          {/* 1 display-1 (超大標題樣式)
             2.  text-primary (主色調: 藍色)
             3.  fw-bold (Font Weight Bold)
          */}
          <h1 className="display-1 fw-bold text-center text-primary">
            您的AI職涯導師
          </h1>
          
          <h2 className="h2 text-center text-secondary mt-4">
            探索我們的功能，開始您的職涯旅程！
          </h2>
          
          {/* 在 MainButton 裡面加上置中的樣式 */}
          <div className="d-flex justify-content-center mt-5">
             <MainButton />
          </div>
        </Container>
      </div>
    </>
  )
}

