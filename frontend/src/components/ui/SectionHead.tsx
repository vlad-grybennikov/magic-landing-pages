import type { CSSProperties } from "react";
import { Eyebrow } from "./Eyebrow";
import { Heading } from "./Heading";
import { Lede } from "./Lede";

export function SectionHead({
  eyebrow,
  heading,
  subhead,
  align = "center",
  size = "lg",
  level = 2,
  className = "",
}: {
  eyebrow?: string;
  heading?: string;
  subhead?: string;
  align?: "left" | "center";
  size?: "sm" | "md" | "lg" | "xl";
  level?: 1 | 2 | 3;
  className?: string;
}) {
  if (!eyebrow && !heading && !subhead) return null;
  const forced = align === "left";
  return (
    <div
      style={
        forced
          ? undefined
          : ({
              alignItems: "var(--sec-items)",
              textAlign: "var(--sec-align)",
            } as unknown as CSSProperties)
      }
      className={`flex flex-col gap-3 ${
        forced ? "items-start text-left" : ""
      } ${className}`}
    >
      {eyebrow && <Eyebrow role="eyebrow">{eyebrow}</Eyebrow>}
      {heading && (
        <Heading level={level} size={size} role="title">
          {heading}
        </Heading>
      )}
      {subhead && (
        <Lede role="description" className="max-w-2xl">
          {subhead}
        </Lede>
      )}
    </div>
  );
}
