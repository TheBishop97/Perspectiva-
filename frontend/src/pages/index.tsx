import { useEffect, useState } from "react";

interface Article {
  id: number;
  title: string;
  url: string;
}

export default function Home() {
  const [articles, setArticles] = useState<Article[]>([]);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await fetch("http://backend:8000/articles"); // container-to-container
        const data = await res.json();
        setArticles(data);
      } catch (err) {
        console.error("Failed to fetch articles:", err);
      }
    }
    fetchData();
  }, []);

  return (
    <main style={{ padding: 20, fontFamily: "sans-serif" }}>
      <h1 style={{ fontSize: 32, fontWeight: "bold" }}>Perspectiva News</h1>
      <div style={{ display: "grid", gap: 16, marginTop: 20 }}>
        {articles.map((a) => (
          <article key={a.id} style={{ border: "1px solid #ddd", padding: 12, borderRadius: 8 }}>
            <a href={a.url} target="_blank" rel="noreferrer" style={{ color: "#0366d6", fontWeight: 600 }}>
              {a.title}
            </a>
            <p>Article ID: {a.id}</p>
          </article>
        ))}
      </div>
    </main>
  );
}
