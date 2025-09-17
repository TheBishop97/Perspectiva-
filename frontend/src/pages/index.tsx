import { useEffect, useState } from "react";

type Article = {
  id: number;
  title: string;
  url: string;
};

export default function Home() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchArticles() {
      try {
        const res = await fetch("http://backend:8000/articles"); 
        if (!res.ok) throw new Error("Failed to fetch articles");
        const data = await res.json();
        setArticles(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchArticles();
  }, []);

  if (loading) return <p className="text-gray-400">Loading articles...</p>;
  if (error) return <p className="text-red-400">Error: {error}</p>;

  return (
    <main className="min-h-screen bg-gray-900 text-white p-6">
      <h1 className="text-3xl font-bold mb-6">Perspectiva News</h1>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {articles.map((a) => (
          <article
            key={a.id}
            className="bg-gray-800 p-4 rounded-2xl shadow-md hover:scale-105 transition-transform duration-200"
          >
            <a
              href={a.url}
              target="_blank"
              rel="noreferrer"
              className="text-blue-400 font-semibold hover:underline"
            >
              {a.title}
            </a>
            <p className="text-sm text-gray-400 mt-2">Article ID: {a.id}</p>
          </article>
        ))}
      </div>
    </main>
  );
}
