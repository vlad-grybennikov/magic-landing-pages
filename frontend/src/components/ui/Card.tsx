import type { ReactNode } from "react";

export function Card({
  tone = "plain",
  className = "",
  children,
  ...rest
}: {
  tone?: "plain" | "muted" | "tinted" | "bare";
  className?: string;
  children: ReactNode;
} & Record<string, unknown>) {
  const tones = {
    plain: "border border-border bg-background",
    muted: "border border-border bg-muted",
    tinted: "border border-primary/15 bg-primary/5",
    bare: "",
  }[tone];
  return (
    <div
      {...rest}
      style={{ boxShadow: tone === "bare" ? undefined : "var(--sec-shadow)" }}
      className={`rounded-[var(--sec-radius)] transition-shadow duration-200 hover:shadow-[var(--sec-shadow-lift)] ${tones} ${className}`}
    >
      {children}
    </div>
  );
}
