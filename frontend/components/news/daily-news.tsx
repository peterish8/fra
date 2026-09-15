"use client";

import { useEffect, useMemo, useState } from "react";

import { fetchCompanyNews, type NewsItem } from "@/lib/news-api-client";

const TRACKED_COMPANIES: Array<{ company: string; symbol: string }> = [
  { company: "NVIDIA", symbol: "NVDA" },
  { company: "Shopify", symbol: "SHOP" },
  { company: "Apple", symbol: "AAPL" },
  { company: "Microsoft", symbol: "MSFT" },
  { company: "Amazon", symbol: "AMZN" },
  { company: "Alphabet", symbol: "GOOGL" },
  { company: "Tesla", symbol: "TSLA" },
  { company: "Meta", symbol: "META" },
  { company: "Netflix", symbol: "NFLX" },
  { company: "AMD", symbol: "AMD" },
];

const PAGE_SIZE = 6;

function timeAgo(publishedAt: string): string {
  const diffMs = Date.now() - new Date(publishedAt).getTime();
  const hours = Math.round(diffMs / (1000 * 60 * 60));
  if (hours < 1) return "Just now";
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

export function DailyNews() {
  const [newsByCompany, setNewsByCompany] = useState<Record<string, NewsItem[]>>({});
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  useEffect(() => {
    let cancelled = false;

    Promise.allSettled(
      TRACKED_COMPANIES.map(async ({ company, symbol }) => {
        const liveItems = await fetchCompanyNews(company, symbol);
        if (cancelled || !liveItems) return;
        setNewsByCompany((current) => ({ ...current, [company]: liveItems }));
      }),
    ).then(() => {
      if (!cancelled) setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  const allItems = useMemo(
    () =>
      Object.values(newsByCompany)
        .flat()
        .sort((a, b) => new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime()),
    [newsByCompany],
  );

  const pageCount = Math.max(1, Math.ceil(allItems.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const items = allItems.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  return (
    <main className="news-page" id="main-content">
      <header className="news-topbar">
        <div>
          <p className="news-kicker">Daily news</p>
          <h1>What companies reported today</h1>
        </div>
        <span className="news-sample-tag">Live headlines · powered by Finnhub</span>
      </header>

      <section className="news-grid" aria-label="Recent headlines">
        {items.map((item) => (
          <article className="news-card" key={item.id}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img className="news-card-image" src={item.imageUrl} alt="" aria-hidden="true" loading="lazy" />
            <div className="news-card-body">
              <div className="news-card-meta">
                <span className="news-card-symbol">{item.symbol}</span>
                <span>{item.source}</span>
                <span aria-hidden="true">·</span>
                <span>{timeAgo(item.publishedAt)}</span>
              </div>
              <h2 className="news-card-headline">{item.headline}</h2>
              <p className="news-card-summary">{item.summary}</p>
              <a className="news-card-link" href={item.url} target="_blank" rel="noreferrer noopener">
                Read source <span aria-hidden="true">→</span>
              </a>
            </div>
          </article>
        ))}
        {items.length === 0 && loading ? <p className="news-empty">Loading live headlines…</p> : null}
        {items.length === 0 && !loading ? (
          <p className="news-empty">No live headlines available right now. Try again shortly.</p>
        ) : null}
      </section>

      {pageCount > 1 ? (
        <nav className="news-pagination" aria-label="News pages">
          <button type="button" disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)}>
            <span aria-hidden="true">←</span> Previous
          </button>
          {Array.from({ length: pageCount }, (_, index) => index + 1).map((pageNumber) => (
            <button
              key={pageNumber}
              type="button"
              aria-current={pageNumber === currentPage ? "page" : undefined}
              className={pageNumber === currentPage ? "news-page-active" : ""}
              onClick={() => setPage(pageNumber)}
            >
              {pageNumber}
            </button>
          ))}
          <button type="button" disabled={currentPage === pageCount} onClick={() => setPage(currentPage + 1)}>
            Next <span aria-hidden="true">→</span>
          </button>
        </nav>
      ) : null}
    </main>
  );
}
