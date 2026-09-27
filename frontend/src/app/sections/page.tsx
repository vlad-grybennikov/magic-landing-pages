import Link from "next/link";
import type { SectionType } from "@/types/sections";
import { PageRenderer } from "@/components/PageRenderer";
import { SparklesIcon } from "@/components/build/icons";
import { variantCount, variantNames } from "@/components/sections/registry";
import {
  DEFAULT_VARIANTS,
  SECTION_LABELS,
  SECTION_ORDER,
} from "@/lib/sections";
import { sampleSection } from "@/data/section-samples";

export const metadata = {
  title: "Section library",
};

/**
 * The section library, as a storybook: one section at a time, drawn with the
 * sample content a generated page would carry, and a row of its layouts to
 * switch between. Every state is a URL, so a layout can be pointed at.
 *
 * Dressed like the builder -- the same bar, ground, panels and chips -- so it
 * reads as a room of the same house rather than a separate tool.
 */
export default async function SectionLibraryPage({
  searchParams,
}: {
  searchParams: Promise<{ type?: string; variant?: string }>;
}) {
  const params = await searchParams;
  const type = (
    SECTION_ORDER.includes(params.type as SectionType) ? params.type : "hero"
  ) as SectionType;
  const variants = variantNames(type) as string[];
  const variant = variants.includes(params.variant ?? "")
    ? params.variant!
    : DEFAULT_VARIANTS[type];

  // The header and footer are drawn with a page around them so their links
  // have somewhere to go.
  const context = SECTION_ORDER.map((kind) => sampleSection(kind));

  return (
    <div className="flex h-dvh flex-col bg-ui-canvas font-ui text-ui-text">
      <header className="flex h-14 shrink-0 items-center gap-2 border-b border-ui-border bg-ui-surface px-3 lg:px-4">
        <div className="flex shrink-0 items-center gap-2.5 pr-1">
          <span className="brand-gradient flex h-7 w-7 items-center justify-center rounded-lg text-white">
            <SparklesIcon className="h-4 w-4" />
          </span>
          <span className="hidden text-sm font-semibold tracking-tight lg:inline">
            Magic Landing Pages
          </span>
        </div>
        <span className="h-4 w-px shrink-0 bg-ui-border" aria-hidden />
        <span className="px-1 text-sm font-medium">Section library</span>
        <span className="text-sm text-ui-faint">
          {variantCount()} layouts across {SECTION_ORDER.length} sections
        </span>
      </header>

      <div className="grid min-h-0 flex-1 gap-4 p-4 lg:grid-cols-[220px_minmax(0,1fr)] lg:gap-5 lg:p-5">
        <aside className="panel flex min-h-0 flex-col overflow-hidden">
          <p className="border-b border-ui-border px-4 py-3 text-[11px] font-medium uppercase tracking-[0.06em] text-ui-faint">
            Sections
          </p>
          <nav className="min-h-0 flex-1 overflow-y-auto p-1.5">
            {SECTION_ORDER.map((kind) => {
              const active = kind === type;
              return (
                <Link
                  key={kind}
                  href={`/sections?type=${kind}`}
                  aria-current={active ? "page" : undefined}
                  className={`flex items-baseline justify-between rounded-lg px-3 py-1.5 text-sm transition-colors ${
                    active
                      ? "bg-ui-accent-soft font-medium text-ui-accent"
                      : "text-ui-muted hover:bg-ui-inset hover:text-ui-text"
                  }`}
                >
                  {SECTION_LABELS[kind]}
                  <span className="text-xs tabular-nums text-ui-faint">
                    {variantNames(kind).length}
                  </span>
                </Link>
              );
            })}
          </nav>
        </aside>

        <main className="panel flex min-h-0 flex-col overflow-hidden">
          <div className="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-2 border-b border-ui-border px-4 py-2.5">
            <h1 className="text-sm font-semibold">{SECTION_LABELS[type]}</h1>
            <span className="h-4 w-px bg-ui-border" aria-hidden />
            <div className="flex flex-wrap items-center gap-1">
              {variants.map((name) => {
                const active = name === variant;
                return (
                  <Link
                    key={name}
                    href={`/sections?type=${type}&variant=${name}`}
                    aria-current={active ? "true" : undefined}
                    className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
                      active
                        ? "bg-ui-accent-soft text-ui-accent"
                        : "text-ui-muted hover:bg-ui-inset hover:text-ui-text"
                    }`}
                  >
                    {name}
                  </Link>
                );
              })}
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto">
            <PageRenderer
              sections={[sampleSection(type, variant)]}
              context={context}
            />
          </div>
        </main>
      </div>
    </div>
  );
}
