import { env } from "../config/env";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly code?: string
  ) {
    super(message);
  }
}

let onUnauthorizedCallback: (() => void) | null = null;

export function setUnauthorizedCallback(cb: () => void) {
  onUnauthorizedCallback = cb;
}

export function getToken(): string | null {
  return localStorage.getItem("spip_token");
}

export function setToken(token: string | null) {
  if (token) {
    localStorage.setItem("spip_token", token);
  } else {
    localStorage.removeItem("spip_token");
  }
}

export async function fetchApi<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  let response: Response;
  try {
    response = await fetch(`${env.apiBaseUrl}${path}`, {
      ...options,
      headers,
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Unable to reach API server.";
    throw new ApiError(0, msg, "NETWORK_ERROR");
  }

  if (response.status === 401) {
    if (onUnauthorizedCallback) {
      onUnauthorizedCallback();
    }
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: string | Array<{ msg: string }>;
      message?: string;
      code?: string;
    } | null;

    let msg = payload?.message || (typeof payload?.detail === "string" ? payload.detail : undefined);
    if (!msg && Array.isArray(payload?.detail) && payload.detail.length > 0) {
      msg = payload.detail.map((d) => d.msg).join(", ");
    }
    if (!msg) {
      msg = `Request failed with status ${response.status}`;
    }

    throw new ApiError(response.status, msg, payload?.code);
  }


  if (response.status === 24) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}

export async function fetchBlob(
  path: string,
  options: RequestInit = {}
): Promise<{ blob: Blob; filename: string; contentType: string }> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let fullUrl: string;
  if (path.startsWith("http://") || path.startsWith("https://")) {
    fullUrl = path;
  } else if (path.startsWith("/api/v1")) {
    const baseWithoutApi = env.apiBaseUrl.replace(/\/api\/v1\/?$/, "");
    fullUrl = `${baseWithoutApi}${path}`;
  } else {
    fullUrl = `${env.apiBaseUrl}${path.startsWith("/") ? "" : "/"}${path}`;
  }

  let response: Response;
  try {
    response = await fetch(fullUrl, {
      ...options,
      headers,
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Unable to reach API server.";
    throw new ApiError(0, msg, "NETWORK_ERROR");
  }

  if (response.status === 401 && onUnauthorizedCallback) {
    onUnauthorizedCallback();
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { message?: string; detail?: string } | null;
    const msg = payload?.message || payload?.detail || `Download failed with status ${response.status}`;
    throw new ApiError(response.status, msg);
  }

  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("text/html") || contentType.includes("application/json")) {
    const text = await response.text();
    let msg = "Server returned invalid non-binary response for file download.";
    try {
      const parsed = JSON.parse(text);
      if (parsed.message || parsed.detail) msg = parsed.message || parsed.detail;
    } catch {}
    throw new ApiError(response.status, msg);
  }

  const disposition = response.headers.get("content-disposition") || "";
  let filename = "";
  if (disposition.includes("filename=")) {
    const match = disposition.match(/filename="?([^";]+)"?/);
    if (match && match[1]) {
      filename = match[1].trim();
    }
  }

  const rawBlob = await response.blob();
  const typedBlob = new Blob([rawBlob], { type: contentType || "application/octet-stream" });

  return { blob: typedBlob, filename, contentType };
}
