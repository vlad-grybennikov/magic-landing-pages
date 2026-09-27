import { createElement } from "react";
import type { Section } from "@/types/sections";
import { DEFAULT_VARIANTS } from "@/lib/sections";
import { SECTION_VARIANTS, variantComponent } from "./registry";

export function SectionRenderer({
  section,
  sections,
}: {
  section: Section;
  sections?: Section[];
}) {
  switch (section.type) {
    case "header": {
      const View = variantComponent(
        SECTION_VARIANTS.header,
        section.variant,
        DEFAULT_VARIANTS.header,
      );
      return createElement(View, { ...section, sections });
    }
    case "footer": {
      const View = variantComponent(
        SECTION_VARIANTS.footer,
        section.variant,
        DEFAULT_VARIANTS.footer,
      );
      return createElement(View, { ...section, sections });
    }
    case "hero": {
      const View = variantComponent(
        SECTION_VARIANTS.hero,
        section.variant,
        DEFAULT_VARIANTS.hero,
      );
      return createElement(View, section);
    }
    case "about": {
      const View = variantComponent(
        SECTION_VARIANTS.about,
        section.variant,
        DEFAULT_VARIANTS.about,
      );
      return createElement(View, section);
    }
    case "benefits": {
      const View = variantComponent(
        SECTION_VARIANTS.benefits,
        section.variant,
        DEFAULT_VARIANTS.benefits,
      );
      return createElement(View, section);
    }
    case "services": {
      const View = variantComponent(
        SECTION_VARIANTS.services,
        section.variant,
        DEFAULT_VARIANTS.services,
      );
      return createElement(View, section);
    }
    case "process": {
      const View = variantComponent(
        SECTION_VARIANTS.process,
        section.variant,
        DEFAULT_VARIANTS.process,
      );
      return createElement(View, section);
    }
    case "stats": {
      const View = variantComponent(
        SECTION_VARIANTS.stats,
        section.variant,
        DEFAULT_VARIANTS.stats,
      );
      return createElement(View, section);
    }
    case "gallery": {
      const View = variantComponent(
        SECTION_VARIANTS.gallery,
        section.variant,
        DEFAULT_VARIANTS.gallery,
      );
      return createElement(View, section);
    }
    case "testimonials": {
      const View = variantComponent(
        SECTION_VARIANTS.testimonials,
        section.variant,
        DEFAULT_VARIANTS.testimonials,
      );
      return createElement(View, section);
    }
    case "pricing": {
      const View = variantComponent(
        SECTION_VARIANTS.pricing,
        section.variant,
        DEFAULT_VARIANTS.pricing,
      );
      return createElement(View, section);
    }
    case "team": {
      const View = variantComponent(
        SECTION_VARIANTS.team,
        section.variant,
        DEFAULT_VARIANTS.team,
      );
      return createElement(View, section);
    }
    case "promotion": {
      const View = variantComponent(
        SECTION_VARIANTS.promotion,
        section.variant,
        DEFAULT_VARIANTS.promotion,
      );
      return createElement(View, section);
    }
    case "faq": {
      const View = variantComponent(
        SECTION_VARIANTS.faq,
        section.variant,
        DEFAULT_VARIANTS.faq,
      );
      return createElement(View, section);
    }
    case "contact": {
      const View = variantComponent(
        SECTION_VARIANTS.contact,
        section.variant,
        DEFAULT_VARIANTS.contact,
      );
      return createElement(View, section);
    }
    case "cta": {
      const View = variantComponent(
        SECTION_VARIANTS.cta,
        section.variant,
        DEFAULT_VARIANTS.cta,
      );
      return createElement(View, section);
    }
    default: {
      const _exhaustive: never = section;
      return _exhaustive;
    }
  }
}
