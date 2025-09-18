"use client";

import { useEffect, useState } from "react";

interface Article {
  id: number;
  title: string;
  url: string;
  summary: string;
  sentiment: string;
}

export default function Home() {
  const [articles, setArticles] = useState<Article[]>([]);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    console.log("Fetching from:", apiUrl);

    fetch(`${apiUrl}/articles`)
      .then((res) => res.json())
      .then((data) => setArticles(data))
      .catch((err) => console.error("Error fetching articles:", err));
  }, []);

  return (
    <main className="p-8">
      <h1 className="text-3xl font-bold mb-6">Latest Articles</h1>
      <ul className="space-y-4">
        {articles.map((article) => (
          <li key={article.id} className="p-4 border rounded-lg shadow">
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xl font-semibold text-blue-600 hover:underline"
            >
              {article.title}
            </a>
            <p className="text-gray-600">{article.summary}</p>
            <span className="text-sm text-gray-500">
              Sentiment: {article.sentiment}
            </span>
          </li>
        ))}
      </ul>
    </main>
  );
}
