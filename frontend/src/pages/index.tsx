import { useEffect, useState } from "react";

type Article = {
  id: number;
  title: string;
  url: string;
};

export default function Home() {
  const [articles, setArticles] = useState<Article[]>([]);

  useEffect(() => {
    async function fetchArticles() {
      try {
        const res = await fetch("http://backend:8000/articles"); 
        // 👆 Notice we call `backend`, the Docker service name in docker-compose.yml
        if (!res.ok) throw new Error("Failed to fetch articles");
        const data = await res.json();
        setArticles(data);
      } catch (err) {
        console.error(err);
      }
    }
    fetchArticles();
  }, []);

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
