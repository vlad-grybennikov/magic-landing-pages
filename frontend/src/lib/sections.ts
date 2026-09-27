import type { SectionType, VariantOf } from "@/types/sections";
import { MANIFEST } from "@/generated/manifest";

export const SECTION_ORDER: SectionType[] = [...MANIFEST.sectionOrder];

export const SECTION_LABELS: Record<SectionType, string> = MANIFEST.sectionLabels;

export const DEFAULT_VARIANTS: { [T in SectionType]: VariantOf<T> } =
  MANIFEST.defaultVariants;

export const LIST_FIELDS: Partial<Record<SectionType, [string, string]>> =
  Object.fromEntries(
    Object.entries(MANIFEST.listFields).map(([kind, [field, label]]) => [
      kind,
      [field, label],
    ]),
  );

export const PINNED_SECTIONS: readonly SectionType[] = MANIFEST.pinnedSections;

export function entryCount(section: { type: SectionType } & Record<string, unknown>) {
  const field = LIST_FIELDS[section.type]?.[0];
  const list = field ? section[field] : undefined;
  return Array.isArray(list) ? list.length : 0;
}

export type LayoutPack = { [T in SectionType]: VariantOf<T> };

export const LAYOUT_PACKS: Record<string, LayoutPack> = MANIFEST.layoutPacks;

export interface PackStyle {
  radius: string;
  headingWeight: string;
  headingTracking: string;
  pad: string;
  align: "left" | "center";
  buttonRadius: string;
  shadow: string;
  shadowLift: string;
  eyebrow: "pill" | "plain" | "rule";
}

export const PACK_STYLES: Record<string, PackStyle> = {
  editorial: {
    radius: "0.375rem",
    headingWeight: "600",
    headingTracking: "-0.022em",
    pad: "clamp(3rem, 5vw, 4.5rem)",
    align: "left",
    buttonRadius: "0.375rem",
    shadow: "0 1px 2px 0 rgb(15 23 42 / 0.04)",
    shadowLift: "0 8px 24px -8px rgb(15 23 42 / 0.12)",
    eyebrow: "rule",
  },
  bold: {
    radius: "1rem",
    headingWeight: "700",
    headingTracking: "-0.032em",
    pad: "clamp(3.5rem, 7vw, 6rem)",
    align: "center",
    buttonRadius: "9999px",
    shadow: "0 4px 16px -4px rgb(15 23 42 / 0.10)",
    shadowLift: "0 20px 40px -12px rgb(15 23 42 / 0.22)",
    eyebrow: "pill",
  },
  minimal: {
    radius: "0.75rem",
    headingWeight: "600",
    headingTracking: "-0.024em",
    pad: "clamp(3.5rem, 7vw, 6rem)",
    align: "center",
    buttonRadius: "9999px",
    shadow: "0 1px 3px 0 rgb(15 23 42 / 0.05)",
    shadowLift: "0 12px 28px -10px rgb(15 23 42 / 0.14)",
    eyebrow: "plain",
  },
  warm: {
    radius: "1.5rem",
    headingWeight: "600",
    headingTracking: "-0.014em",
    pad: "clamp(3rem, 5.5vw, 5rem)",
    align: "center",
    buttonRadius: "9999px",
    shadow: "0 6px 20px -6px rgb(15 23 42 / 0.10)",
    shadowLift: "0 18px 36px -12px rgb(15 23 42 / 0.18)",
    eyebrow: "pill",
  },
  corporate: {
    radius: "0.5rem",
    headingWeight: "600",
    headingTracking: "-0.022em",
    pad: "clamp(3rem, 5vw, 4.5rem)",
    align: "center",
    buttonRadius: "0.5rem",
    shadow: "0 2px 8px -2px rgb(15 23 42 / 0.08)",
    shadowLift: "0 14px 30px -10px rgb(15 23 42 / 0.16)",
    eyebrow: "pill",
  },
  boutique: {
    radius: "1.75rem",
    headingWeight: "500",
    headingTracking: "-0.01em",
    pad: "clamp(3.5rem, 7vw, 6rem)",
    align: "left",
    buttonRadius: "9999px",
    shadow: "0 8px 30px -10px rgb(15 23 42 / 0.12)",
    shadowLift: "0 24px 48px -16px rgb(15 23 42 / 0.20)",
    eyebrow: "plain",
  },
  technical: {
    radius: "0.25rem",
    headingWeight: "600",
    headingTracking: "-0.02em",
    pad: "clamp(2.5rem, 4vw, 3.5rem)",
    align: "left",
    buttonRadius: "0.25rem",
    shadow: "0 1px 2px 0 rgb(15 23 42 / 0.06)",
    shadowLift: "0 6px 16px -6px rgb(15 23 42 / 0.12)",
    eyebrow: "rule",
  },
  organic: {
    radius: "2rem",
    headingWeight: "500",
    headingTracking: "-0.004em",
    pad: "clamp(3.5rem, 6.5vw, 5.5rem)",
    align: "center",
    buttonRadius: "9999px",
    shadow: "0 6px 24px -8px rgb(15 23 42 / 0.10)",
    shadowLift: "0 20px 44px -14px rgb(15 23 42 / 0.18)",
    eyebrow: "pill",
  },
  luxe: {
    radius: "0rem",
    headingWeight: "400",
    headingTracking: "-0.008em",
    pad: "clamp(4rem, 8vw, 7rem)",
    align: "left",
    buttonRadius: "0rem",
    shadow: "0 1px 2px 0 rgb(15 23 42 / 0.04)",
    shadowLift: "0 16px 40px -12px rgb(15 23 42 / 0.16)",
    eyebrow: "rule",
  },
};

const EYEBROW_STYLES: Record<PackStyle["eyebrow"], Record<string, string>> = {
  pill: {
    "--sec-eyebrow-bg": "color-mix(in oklab, var(--primary) 10%, transparent)",
    "--sec-eyebrow-pad": "0.4rem 0.8rem",
    "--sec-eyebrow-radius": "9999px",
    "--sec-eyebrow-rule": "0px",
  },
  plain: {
    "--sec-eyebrow-bg": "transparent",
    "--sec-eyebrow-pad": "0",
    "--sec-eyebrow-radius": "0",
    "--sec-eyebrow-rule": "0px",
  },
  rule: {
    "--sec-eyebrow-bg": "transparent",
    "--sec-eyebrow-pad": "0",
    "--sec-eyebrow-radius": "0",
    "--sec-eyebrow-rule": "2rem",
  },
};

export function packStyleVars(pack?: string | null): Record<string, string> {
  const style = pack ? PACK_STYLES[pack] : undefined;
  if (!style) return {};
  return {
    "--sec-radius": style.radius,
    "--sec-heading-weight": style.headingWeight,
    "--sec-heading-tracking": style.headingTracking,
    "--sec-pad": style.pad,
    "--sec-align": style.align,
    "--sec-items": style.align === "center" ? "center" : "flex-start",
    "--sec-btn-radius": style.buttonRadius,
    "--sec-shadow": style.shadow,
    "--sec-shadow-lift": style.shadowLift,
    ...EYEBROW_STYLES[style.eyebrow],
  };
}

export const LAYOUT_PACK_NAMES = Object.keys(LAYOUT_PACKS);

export const DEFAULT_LAYOUT_PACK: string = MANIFEST.defaultLayoutPack;
