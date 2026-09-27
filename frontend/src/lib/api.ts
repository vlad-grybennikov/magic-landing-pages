import { authHeaders, refreshAccess } from "@/lib/auth";

export const BASE_URL =
  process.env.NEXT_PUBLIC_ORCHESTRATOR_URL ?? "http://localhost:8000";

export async function authedFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const send = () =>
    fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: { ...(init.headers ?? {}), ...authHeaders() },
    });

  const response = await send();
  if (response.status !== 401) return response;
  return (await refreshAccess()) ? send() : response;
}
