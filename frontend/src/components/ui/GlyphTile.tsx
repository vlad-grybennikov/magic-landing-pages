import type { ImageRef } from "@/types/sections";
import { Glyph } from "./Glyph";
import { el } from "./marks";

export function GlyphTile({
  icon,
  path,
  shape = "rounded",
  tone = "tint",
}: {
  icon?: ImageRef;
  path?: string;
  shape?: "rounded" | "circle" | "square";
  tone?: "tint" | "solid" | "outline";
}) {
  const radius = {
    rounded: "rounded-2xl",
    circle: "rounded-full",
    square: "rounded-none",
  }[shape];
  const tones = {
    tint: "bg-primary/10 text-primary",
    solid: "bg-primary text-primary-foreground",
    outline: "border border-border bg-background text-primary",
  }[tone];

  return (
    <span
      {...(path ? el(path, "Icon") : {})}
      style={{ boxShadow: tone === "tint" ? undefined : "var(--sec-shadow)" }}
      className={`flex h-16 w-16 items-center justify-center ${radius} ${tones}`}
    >
      <Glyph icon={icon} size={32} className="" />
    </span>
  );
}
