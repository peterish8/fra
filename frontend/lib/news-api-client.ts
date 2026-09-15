export type NewsItem = {
  id: string;
  company: string;
  symbol: string;
  headline: string;
  summary: string;
  source: string;
  publishedAt: string;
  url: string;
  imageUrl: string;
};

type BackendNewsItem = {
  headline: string;
  summary: string | null;
  url: string;
  image_url: string | null;
  source: string;
  published_at: string;
  related_symbol: string | null;
};

type BackendNewsResponse = {
  status: string;
  items: BackendNewsItem[];
  reason: string | null;
};

// Finnhub falls back to the source outlet's generic logo (e.g. Yahoo
// Finance's own branding) when an article has no real photo. Showing that
// same logo on every card looks broken, so treat it as "no image" instead.
const GENERIC_PLACEHOLDER_IMAGE_PATTERNS = [/s\.yimg\.com\/rz\/stage/i, /yahoo_finance.*\.png$/i];

function isGenericPlaceholderImage(url: string): boolean {
  return GENERIC_PLACEHOLDER_IMAGE_PATTERNS.some((pattern) => pattern.test(url));
}

/** Fetch real company news from the backend; returns null when unavailable (no key, no results, or a request failure). */
export async function fetchCompanyNews(
  company: string,
  symbol: string,
  limit = 5,
): Promise<NewsItem[] | null> {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!baseUrl) return null;

  let response: Response;
  try {
    response = await fetch(
      `${baseUrl}/v1/news?symbol=${encodeURIComponent(symbol)}&limit=${limit}`,
      { headers: { Accept: "application/json" } },
    );
  } catch {
    return null;
  }
  if (!response.ok) return null;

  let payload: BackendNewsResponse;
  try {
    payload = (await response.json()) as BackendNewsResponse;
  } catch {
    return null;
  }
  if (payload.status !== "SUCCESS" || payload.items.length === 0) return null;

  return payload.items.map((item, index) => {
    const hasRealImage = item.image_url && !isGenericPlaceholderImage(item.image_url);
    return {
      id: `${symbol}-${index}-${item.url}`,
      company,
      symbol,
      headline: item.headline,
      summary: item.summary ?? "",
      source: item.source,
      publishedAt: item.published_at,
      url: item.url,
      imageUrl: hasRealImage
        ? (item.image_url as string)
        : `https://picsum.photos/seed/${encodeURIComponent(symbol)}-${index}/640/360`,
    };
  });
}
