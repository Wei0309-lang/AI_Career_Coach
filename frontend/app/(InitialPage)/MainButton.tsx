"use client";

import Image from "next/image";
import Link from "next/link";
import { Container, Row, Col, Card } from "react-bootstrap";

export default function MainButton() {
  const features = [
    {
      name: "AI模擬面試",
      href: "/chat",
      description: "與 AI 職涯教練進行對話，獲取職涯建議。",
      color: "primary", // blue -> primary
      img: "/InitialPageImg/AiInterview.png",
    },
    {
      name: "履歷健檢",
      href: "/check",
      description: "完成職涯測評，了解自己的職業傾向。",
      color: "success", // green -> success
      img: "/InitialPageImg/AiResume.png",
    },
    {
      name: "職涯探索",
      href: "/resources",
      description: "獲取個性化的職涯資源推薦。",
      color: "danger", // red -> danger
      img: "/InitialPageImg/AiCareer.jpg",
    },
  ];

  return (
    <Container className="my-5">
      
      <Row className="g-4 justify-content-center">
        {features.map((feature) => (
          <Col md={4} key={feature.name}>
            <Link href={feature.href} className="text-decoration-none">
              <Card 
                className={`h-100 shadow border-top border-4 border-${feature.color} hover-shadow`}
                style={{ transition: "transform 0.2s" }}
              >
                <Card.Body className="text-center p-4">
                  {/* 標題顏色 */}
                  <h2 className={`h3 fw-bold text-${feature.color} mb-3`}>
                    {feature.name}
                  </h2>
                  
                  <Card.Text className="text-secondary mb-4">
                    {feature.description}
                  </Card.Text>

                  {/* 圖片區域 */}
                  <div style={{ position: "relative", height: "200px" }}>
                    <Image
                      src={feature.img}
                      alt={feature.name}
                      width={500}
                      height={500}
                      style={{ 
                        width: "100%", 
                        height: "100%", 
                        objectFit: "contain" // 保持圖片比例
                      }}
                    />
                  </div>
                </Card.Body>
              </Card>
            </Link>
          </Col>
        ))}
      </Row>
      
      {/* 為了讓 hover 效果更像原本的，加自訂樣式 */}
      <style jsx global>{`
        .hover-shadow:hover {
          box-shadow: 0 1rem 3rem rgba(0,0,0,.175)!important;
          transform: translateY(-5px);
        }
      `}</style>
    </Container>
  );
}