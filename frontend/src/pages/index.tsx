import { useEffect, useState } from "react";

export default function Home() {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Use relative path so it works whether served from localhost, VPS IP or domain
    fetch("/api/articles")
      .then((r) => r.json())
      .then((data) => {
        setArticles(data || []);
      })
      .catch((err) => {
        console.error("Failed to load articles", err);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: 24 }}>
      <h1>Perspectiva — Recent Articles</h1>

      {loading && <p>Loading…</p>}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(280px,1fr))", gap: 16, marginTop: 20 }}>
        {articles.map((a) => (
          <article key={a.id} style={{ border: "1px solid #ddd", padding: 12, borderRadius: 8 }}>
            <a href={a.url} target="_blank" rel="noreferrer" style={{ color: "#0366d6", fontWeight: 600, display: "block", marginBottom: 8 }}>
              {a.title}
            </a>
            <div style={{ fontSize: 12, color: "#555" }}>{a.source_id ? a.source_id : ""} — {a.published_at ? new Date(a.published_at).toLocaleString() : ""}</div>
            <p style={{ marginTop: 8, fontSize: 14 }}>{a.summary ? a.summary : (a.full_text ? a.full_text.slice(0, 200) + "…" : "")}</p>
            <div style={{ marginTop: 8, fontSize: 12 }}>Sentiment: {a.sentiment || "—"}</div>
          </article>
        ))}
      </div>
    </main>
  );
}
