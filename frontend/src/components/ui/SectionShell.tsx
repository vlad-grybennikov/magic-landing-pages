import type { ReactNode } from "react";

export function SectionShell({
  type,
  tone = "plain",
  className = "",
  children,
}: {
  type: string;
  tone?: "plain" | "muted" | "tinted" | "accent";
  className?: string;
  children: ReactNode;
}) {
  const tones = {
    plain: "bg-background text-foreground",
    muted:
      "border-y border-border/60 bg-muted text-foreground " +
      "bg-[linear-gradient(to_bottom,color-mix(in_oklab,var(--primary)_4%,var(--muted)),var(--muted))]",
    tinted:
      "text-foreground bg-[radial-gradient(80%_60%_at_50%_0%,color-mix(in_oklab,var(--primary)_12%,var(--background)),var(--background))]",
    accent:
      "text-primary-foreground bg-[radial-gradient(90%_70%_at_50%_0%,color-mix(in_oklab,white_14%,var(--primary)),var(--primary))]",
  };
  return (
    <section
      id={type}
      data-section={type}
      className={`relative w-full scroll-mt-16 ${tones[tone]} ${className}`}
    >
      {children}
    </section>
  );
}
