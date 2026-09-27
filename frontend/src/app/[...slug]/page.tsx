import { notFound } from "next/navigation";
import { PageRenderer } from "@/components/PageRenderer";
import { getPageByUrl } from "@/lib/page";

export default async function GeneratedPage({
  params,
}: {
  params: Promise<{ slug: string[] }>;
}) {
  const { slug } = await params;
  const url = "/" + slug.join("/");

  const page = await getPageByUrl(url);
  if (!page) notFound();

  return <PageRenderer sections={page.sections} theme={page.theme} />;
}
