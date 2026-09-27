import { MANIFEST } from "@/generated/manifest";

export interface ImageRef {
  src: string;
  alt: string;
  id?: string | null;
  category?: string | null;
  photographer?: string | null;
  photographer_url?: string | null;
  source_url?: string | null;
}

export interface BrandRef {
  name: string;
  icon: ImageRef;
  tagline?: string | null;
}

export interface ButtonRef {
  label: string;
  href?: string;
}

export interface NavLinkRef {
  label: string;
  href: string;
}

export interface HeaderSection {
  type: "header";
  name: string;
  icon: ImageRef;
  links?: NavLinkRef[];
  button?: ButtonRef;
  variant?: HeaderVariant;
  anchor?: string;
}

export interface FooterSection {
  type: "footer";
  name: string;
  icon: ImageRef;
  tagline?: string | null;
  links_label?: string | null;
  links?: NavLinkRef[];
  contacts_label?: string | null;
  contacts?: NavLinkRef[];
  copyright?: string | null;
  variant?: FooterVariant;
  anchor?: string;
}

export interface HeroSection {
  type: "hero";
  headline: string;
  subhead?: string;
  image: ImageRef;
  button: ButtonRef;
  variant?: HeroVariant;
  anchor?: string;
}

export interface BenefitItem {
  icon: ImageRef;
  title: string;
  caption: string;
}

export interface BenefitsSection {
  type: "benefits";
  heading: string;
  subhead?: string;
  items: BenefitItem[];
  variant?: BenefitsVariant;
  anchor?: string;
}

export interface PromotionSection {
  type: "promotion";
  title: string;
  description: string;
  button: ButtonRef;
  variant?: PromotionVariant;
  anchor?: string;
}

export interface TestimonialItem {
  name: string;
  rating: number;
  content: string;
}

export interface TestimonialsSection {
  type: "testimonials";
  heading?: string;
  subhead?: string;
  items: TestimonialItem[];
  variant?: TestimonialsVariant;
  anchor?: string;
}

export interface FAQItem {
  question: string;
  answer: string;
}

export interface FAQSection {
  type: "faq";
  heading?: string;
  subhead?: string;
  items: FAQItem[];
  variant?: FaqVariant;
  anchor?: string;
}

export interface ServiceItem {
  title: string;
  caption: string;
  image: ImageRef;
  button?: ButtonRef;
}

export interface ServicesSection {
  type: "services";
  heading: string;
  subhead?: string;
  items: ServiceItem[];
  variant?: ServicesVariant;
  anchor?: string;
}

export interface AboutSection {
  type: "about";
  heading: string;
  eyebrow?: string;
  body: string[];
  image: ImageRef;
  button?: ButtonRef;
  variant?: AboutVariant;
  anchor?: string;
}

export interface ProcessStep {
  title: string;
  caption: string;
  icon?: ImageRef;
}

export interface ProcessSection {
  type: "process";
  heading: string;
  subhead?: string;
  items: ProcessStep[];
  variant?: ProcessVariant;
  anchor?: string;
}

export interface StatItem {
  value: string;
  label: string;
  caption?: string;
}

export interface StatsSection {
  type: "stats";
  heading?: string;
  subhead?: string;
  items: StatItem[];
  variant?: StatsVariant;
  anchor?: string;
}

export interface GallerySection {
  type: "gallery";
  heading?: string;
  subhead?: string;
  images: ImageRef[];
  variant?: GalleryVariant;
  anchor?: string;
}

export interface PricingPlan {
  name: string;
  price: string;
  period?: string;
  description?: string;
  features: string[];
  button: ButtonRef;
  featured?: boolean;
}

export interface PricingSection {
  type: "pricing";
  heading: string;
  subhead?: string;
  plans: PricingPlan[];
  variant?: PricingVariant;
  anchor?: string;
}

export interface TeamMember {
  name: string;
  role: string;
  photo?: ImageRef;
  bio?: string;
}

export interface TeamSection {
  type: "team";
  heading: string;
  subhead?: string;
  members: TeamMember[];
  variant?: TeamVariant;
  anchor?: string;
}

export interface ContactDetail {
  label: string;
  value: string;
  icon?: ImageRef;
}

export interface ContactSection {
  type: "contact";
  heading: string;
  description?: string;
  details: ContactDetail[];
  button?: ButtonRef;
  image?: ImageRef;
  variant?: ContactVariant;
  anchor?: string;
}

export interface CtaSection {
  type: "cta";
  headline: string;
  subhead?: string;
  button: ButtonRef;
  secondary?: ButtonRef;
  image?: ImageRef;
  variant?: CtaVariant;
  anchor?: string;
}

export type Section =
  | HeaderSection
  | HeroSection
  | AboutSection
  | BenefitsSection
  | ServicesSection
  | ProcessSection
  | StatsSection
  | GallerySection
  | TestimonialsSection
  | PricingSection
  | TeamSection
  | PromotionSection
  | FAQSection
  | ContactSection
  | CtaSection
  | FooterSection;

export type SectionType = Section["type"];

export type SectionOf<T extends SectionType> = Extract<Section, { type: T }>;

export type HeaderVariant = (typeof MANIFEST.variants.header)[number];

export type FooterVariant = (typeof MANIFEST.variants.footer)[number];

export type HeroVariant = (typeof MANIFEST.variants.hero)[number];

export type BenefitsVariant = (typeof MANIFEST.variants.benefits)[number];

export type ServicesVariant = (typeof MANIFEST.variants.services)[number];

export type AboutVariant = (typeof MANIFEST.variants.about)[number];

export type ProcessVariant = (typeof MANIFEST.variants.process)[number];

export type StatsVariant = (typeof MANIFEST.variants.stats)[number];

export type GalleryVariant = (typeof MANIFEST.variants.gallery)[number];

export type TestimonialsVariant = (typeof MANIFEST.variants.testimonials)[number];

export type PricingVariant = (typeof MANIFEST.variants.pricing)[number];

export type TeamVariant = (typeof MANIFEST.variants.team)[number];

export type FaqVariant = (typeof MANIFEST.variants.faq)[number];

export type PromotionVariant = (typeof MANIFEST.variants.promotion)[number];

export type ContactVariant = (typeof MANIFEST.variants.contact)[number];

export type CtaVariant = (typeof MANIFEST.variants.cta)[number];

export type VariantOf<T extends SectionType> = NonNullable<
  SectionOf<T>["variant"]
>;

export interface Theme {
  name: string;
  mood?: string | null;
  primary: string;
  primary_strong: string;
  primary_light: string;
  primary_foreground: string;
  accent: string;
  accent_foreground: string;
  background: string;
  foreground: string;
  muted: string;
  muted_foreground: string;
  border: string;
  layout?: string | null;
  font?: string | null;
}

export interface PageData {
  sections: Section[];
  brand?: BrandRef | null;
  name?: string;
  theme?: Theme | null;
}
