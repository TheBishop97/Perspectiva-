import { useEffect, useState } from "react";

// ✅ Define the shape of an Article
interface Article {
  id: number;
  title: string;
  url: string;
}

// ✅ Home page component
export default function Home() {
  const [articles, setArticles] = useState<Article[]>([]);

  // Mock fetch (later you can connect to FastAPI)
  useEffect(() => {
    // Pretend this comes from your backend API
    const mockArticles: Article[] = [
      { id: 1, title: "Welcome to Perspectiva!", url: "https://example.com/1" },
      { id: 2, title: "Next.js Static Export Works!", url: "https://example.com/2" },
      { id: 3, title: "FastAPI + Next.js = 🚀", url: "https://example.com/3" },
    ];
    setArticles(mockArticles);
  }, []);

  return (
    <main style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h1 style={{ fontSize: "2rem", fontWeight: "bold", marginBottom: "1rem" }}>
        Perspectiva News
      </h1>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: "1rem",
        }}
      >
        {articles.map((a) => (
          <article
            key={a.id}
            style={{
              border: "1px solid #ddd",
              padding: "1rem",
              borderRadius: "8px",
              backgroundColor: "#fafafa",
            }}
          >
            <a
              href={a.url}
              target="_blank"
              rel="noreferrer"
              style={{
                color: "#0366d6",
                fontWeight: 600,
                display: "block",
                marginBottom: "0.5rem",
              }}
            >
              {a.title}
            </a>
            <p style={{ fontSize: "0.9rem", color: "#555" }}>
              Article ID: {a.id}
            </p>
          </article>
        ))}
      </div>
    </main>
  );
}
