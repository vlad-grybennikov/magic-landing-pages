import type { components } from "@/generated/api";
import type { Section, Theme } from "@/types/sections";
import type { Brief, VersionEntry } from "@/lib/orchestrator";
import { authedFetch } from "@/lib/api";

type Schemas = components["schemas"];

export type BuildSummary = Schemas["BuildSummary"];
export type SavedMessage = Schemas["SavedMessage"];

export interface BuildDetail extends Omit<Schemas["BuildDetail"], "brief"> {
  brief?: Brief | null;
}

export interface BuildPage
  extends Omit<Schemas["PageView"], "sections" | "theme"> {
  sections: Section[];
  theme?: Theme | null;
}

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await authedFetch(path, {
    ...init,
    headers: {
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) throw new Error(`Orchestrator returned ${res.status}`);
  return res.json();
}

export async function listBuilds(): Promise<BuildSummary[]> {
  const { builds } = await call<{ builds: BuildSummary[] }>("/builds");
  return builds;
}

export async function createBuild(): Promise<BuildSummary> {
  return call<BuildSummary>("/builds", { method: "POST" });
}

export async function openBuild(id: string): Promise<{
  build: BuildDetail;
  page: BuildPage | null;
  versions: VersionEntry[];
}> {
  return call(`/builds/${id}`);
}

export async function saveBuild(
  id: string,
  changes: {
    title?: string;
    messages?: SavedMessage[];
    brief?: Brief;
    summary?: string;
  },
): Promise<BuildSummary> {
  return call<BuildSummary>(`/builds/${id}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}

export async function attachPage(
  id: string,
  pageId: string,
): Promise<BuildSummary> {
  return call<BuildSummary>(`/builds/${id}/page`, {
    method: "PUT",
    body: JSON.stringify({ page_id: pageId }),
  });
}

export async function deleteBuild(id: string): Promise<void> {
  await call(`/builds/${id}`, { method: "DELETE" });
}
