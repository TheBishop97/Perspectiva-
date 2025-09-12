"use client";

import { useEffect, useState } from "react";

interface Article {
  id: number;
  title: string;
  link: string;
  published: string;
  source: string;
}

export default function Home() {
  const [articles, setArticles] = useState<Article[]>([]);

  useEffect(() => {
    fetch("http://localhost:8000/api/articles") // adjust later for VPS domain
      .then((res) => res.json())
      .then((data) => setArticles(data));
  }, []);

  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <h1 className="text-3xl font-bold mb-6 text-gray-800">
        Perspectiva News
      </h1>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {articles.map((a) => (
          <a
            key={a.id}
            href={a.link}
            target="_blank"
            rel="noopener noreferrer"
            className="p-4 bg-white rounded-xl shadow hover:shadow-lg transition"
          >
            <h2 className="text-xl font-semibold text-blue-600">{a.title}</h2>
            <p className="text-sm text-gray-500">
              {new Date(a.published).toLocaleString()} – {a.source}
            </p>
          </a>
        ))}
      </div>
    </main>
  );
}
