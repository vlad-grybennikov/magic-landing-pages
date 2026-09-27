import type { ReactNode } from "react";
import { rich } from "@/lib/richtext";

export function Heading({
  children,
  level = 2,
  size = "lg",
  role,
  className = "",
}: {
  children: ReactNode;
  level?: 1 | 2 | 3;
  size?: "sm" | "md" | "lg" | "xl";
  role?: "title";
  className?: string;
}) {
  const sizes = {
    sm: "text-xl leading-snug sm:text-2xl",
    md: "text-2xl leading-tight sm:text-3xl",
    lg: "text-[2rem] leading-[1.12] sm:text-[2.75rem] lg:text-5xl",
    xl: "text-[2.5rem] leading-[1.05] sm:text-6xl lg:text-[4.25rem]",
  };
  const Tag = (["h1", "h2", "h3"] as const)[level - 1];
  return (
    <Tag
      style={{
        fontFamily: "var(--font-heading)",
        fontWeight: "var(--sec-heading-weight)",
        letterSpacing: "var(--sec-heading-tracking)",
      }}
      data-role={role}
      data-raw={typeof children === "string" ? children : undefined}
      className={`text-balance ${sizes[size]} ${className}`}
    >
      {typeof children === "string" ? rich(children) : children}
    </Tag>
  );
}
