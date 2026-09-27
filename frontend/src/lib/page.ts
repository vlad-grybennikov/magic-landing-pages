import type { PageData, Section, Theme } from "@/types/sections";
import { getDb } from "@/lib/mongodb";

interface PublishedSnapshot {
  version: number;
  name?: string;
  sections: Section[];
  theme?: Theme | null;
  when: string;
}

export async function getPageByUrl(url: string): Promise<PageData | null> {
  const db = await getDb();
  const doc = await db
    .collection("pages")
    .findOne({ url, published: { $ne: null } }, { projection: { published: 1 } });

  const published = doc?.published as PublishedSnapshot | undefined;
  if (!published || !Array.isArray(published.sections)) return null;

  return {
    sections: published.sections,
    theme: published.theme ?? null,
    brand: null,
    name: published.name ?? "",
  };
}
