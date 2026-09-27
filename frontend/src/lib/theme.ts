import type { CSSProperties } from "react";
import type { Theme } from "@/types/sections";

export function themeVars(theme?: Theme | null): CSSProperties {
  if (!theme) return {};
  return {
    "--background": theme.background,
    "--foreground": theme.foreground,
    "--primary": theme.primary,
    "--primary-strong": theme.primary_strong,
    "--primary-light": theme.primary_light,
    "--primary-foreground": theme.primary_foreground,
    "--accent": theme.accent,
    "--accent-foreground": theme.accent_foreground,
    "--muted": theme.muted,
    "--muted-foreground": theme.muted_foreground,
    "--border": theme.border,
  } as CSSProperties;
}

export const BRAND_COLORS = [
  { key: "primary", label: "Brand", hint: "Headings, links and icons" },
  { key: "accent", label: "Buttons", hint: "Calls to action" },
  { key: "background", label: "Page", hint: "The surface behind everything" },
] as const;

export const HEX = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i;
