export type AuthenticatedApiClientOptions = {
  accessToken: string;
  baseUrl: string;
  fetchImplementation?: typeof fetch;
};

export class ApiClientError extends Error {
  readonly status: number;
  readonly statusText: string;

  constructor(status: number, statusText: string, message: string) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.statusText = statusText;
  }
}

type RequestOptions = Omit<RequestInit, "headers"> & {
  headers?: HeadersInit;
};

function toHeaderRecord(headers: HeadersInit | undefined): Record<string, string> {
  const normalized = new Headers(headers);
  const result: Record<string, string> = {};

  normalized.forEach((value, key) => {
    result[key] = value;
  });

  return result;
}

function buildUrl(baseUrl: string, path: string): string {
  const trimmedBaseUrl = baseUrl.replace(/\/+$/, "");

  if (!path.startsWith("/")) {
    throw new Error("Authenticated API paths must be relative and begin with '/'.");
  }

  return `${trimmedBaseUrl}${path}`;
}

async function readErrorMessage(response: Response): Promise<string> {
  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    const payload: unknown = await response.json().catch(() => undefined);

    if (typeof payload === "object" && payload !== null && "error" in payload) {
      const error = payload.error;

      if (typeof error === "object" && error !== null && "message" in error) {
        const message = error.message;
        if (typeof message === "string" && message.length > 0) {
          return message;
        }
      }
    }
  }

  return response.statusText || "The request could not be completed.";
}

export function createAuthenticatedApiClient({
  accessToken,
  baseUrl,
  fetchImplementation = fetch,
}: AuthenticatedApiClientOptions) {
  if (accessToken.trim().length === 0) {
    throw new Error("An authenticated API client requires a user access token.");
  }

  if (baseUrl.trim().length === 0) {
    throw new Error("An authenticated API client requires a backend base URL.");
  }

  async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const headers = toHeaderRecord(options.headers);
    headers.Accept ??= "application/json";
    headers.Authorization = `Bearer ${accessToken}`;

    const response = await fetchImplementation(buildUrl(baseUrl, path), {
      ...options,
      credentials: "omit",
      headers,
    });

    if (!response.ok) {
      throw new ApiClientError(
        response.status,
        response.statusText,
        await readErrorMessage(response),
      );
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return (await response.json()) as T;
  }

  return {
    get<T>(path: string, options?: Omit<RequestOptions, "method" | "body">) {
      return request<T>(path, { ...options, method: "GET" });
    },
    post<T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method" | "body">) {
      const headers = toHeaderRecord(options?.headers);
      headers["Content-Type"] ??= "application/json";

      return request<T>(path, {
        ...options,
        method: "POST",
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    },
    delete<T>(path: string, options?: Omit<RequestOptions, "method" | "body">) {
      return request<T>(path, { ...options, method: "DELETE" });
    },
  };
}
