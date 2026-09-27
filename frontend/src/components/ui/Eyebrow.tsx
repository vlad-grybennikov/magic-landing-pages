import type { ReactNode } from "react";

export function Eyebrow({
  children,
  role,
  className = "",
}: {
  children: ReactNode;
  role?: "eyebrow";
  className?: string;
}) {
  return (
    <p
      data-role={role}
      style={{
        background: "var(--sec-eyebrow-bg, transparent)",
        padding: "var(--sec-eyebrow-pad, 0)",
        borderRadius: "var(--sec-eyebrow-radius, 0)",
      }}
      className={`inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-primary before:h-px before:w-[var(--sec-eyebrow-rule,0px)] before:bg-primary/40 before:content-[''] ${className}`}
    >
      {children}
    </p>
  );
}
