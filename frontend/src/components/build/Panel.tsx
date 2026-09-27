import type { ReactNode } from "react";

export function Panel({
  title,
  aside,
  children,
}: {
  title: string;
  aside?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section>
      <header className="flex items-center justify-between gap-3 border-b border-ui-border px-4 py-3">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ui-faint">
          {title}
        </h2>
        {aside}
      </header>
      <div className="p-4">{children}</div>
    </section>
  );
}

export const inputClass =
  "w-full rounded-lg border border-ui-border bg-ui-surface px-3 py-2 text-sm text-ui-text " +
  "outline-none transition-colors placeholder:text-ui-faint " +
  "focus:border-ui-accent focus:ring-2 focus:ring-ui-accent/15 disabled:opacity-50";
