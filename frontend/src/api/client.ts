import { env } from "../config/env";

export class ApiError extends Error {
  constructor(public readonly status: number, message: string, public readonly requestId?: string) {
    super(message);
  }
}

export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${env.apiBaseUrl}${path}`, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { message?: string; request_id?: string } | null;
    throw new ApiError(response.status, payload?.message ?? "Unable to complete the request.", payload?.request_id);
  }
  return response.json() as Promise<T>;
}
