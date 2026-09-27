import type { ComponentType } from "react";
import type { Section, SectionOf, SectionType, VariantOf } from "@/types/sections";
import { ABOUT_VARIANTS } from "./About";
import { BENEFITS_VARIANTS } from "./Benefits";
import { CONTACT_VARIANTS } from "./Contact";
import { CTA_VARIANTS } from "./Cta";
import { FAQ_VARIANTS } from "./Faq";
import { FOOTER_VARIANTS } from "./Footer";
import { HEADER_VARIANTS } from "./Header";
import { GALLERY_VARIANTS } from "./Gallery";
import { HERO_VARIANTS } from "./Hero";
import { PRICING_VARIANTS } from "./Pricing";
import { PROCESS_VARIANTS } from "./Process";
import { PROMOTION_VARIANTS } from "./Promotion";
import { SERVICES_VARIANTS } from "./Services";
import { STATS_VARIANTS } from "./Stats";
import { TEAM_VARIANTS } from "./Team";
import { TESTIMONIALS_VARIANTS } from "./Testimonials";

export type VariantsOf<T extends SectionType> = Record<
  VariantOf<T>,
  ComponentType<SectionOf<T> & { sections?: Section[] }>
>;

export const SECTION_VARIANTS: { [T in SectionType]: VariantsOf<T> } = {
  header: HEADER_VARIANTS,
  footer: FOOTER_VARIANTS,
  hero: HERO_VARIANTS,
  about: ABOUT_VARIANTS,
  benefits: BENEFITS_VARIANTS,
  services: SERVICES_VARIANTS,
  process: PROCESS_VARIANTS,
  stats: STATS_VARIANTS,
  gallery: GALLERY_VARIANTS,
  testimonials: TESTIMONIALS_VARIANTS,
  pricing: PRICING_VARIANTS,
  team: TEAM_VARIANTS,
  promotion: PROMOTION_VARIANTS,
  faq: FAQ_VARIANTS,
  contact: CONTACT_VARIANTS,
  cta: CTA_VARIANTS,
};

export function variantComponent<T extends SectionType>(
  variants: VariantsOf<T>,
  variant: VariantOf<T> | undefined,
  fallback: VariantOf<T>,
): ComponentType<SectionOf<T> & { sections?: Section[] }> {
  return (variant && variants[variant]) || variants[fallback];
}

export function variantNames<T extends SectionType>(type: T): VariantOf<T>[] {
  return Object.keys(SECTION_VARIANTS[type]) as VariantOf<T>[];
}

export function variantCount(): number {
  return Object.values(SECTION_VARIANTS).reduce(
    (total, variants) => total + Object.keys(variants).length,
    0,
  );
}
