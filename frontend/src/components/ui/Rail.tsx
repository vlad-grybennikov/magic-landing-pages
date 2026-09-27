import type { ReactNode } from "react";

export function Rail({
  className = "",
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={`-mx-6 flex snap-x snap-mandatory gap-5 overflow-x-auto px-6 pb-4 [scrollbar-width:thin] ${className}`}
    >
      {children}
    </div>
  );
}
