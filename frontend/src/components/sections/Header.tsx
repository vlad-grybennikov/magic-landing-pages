import type { ComponentType } from "react";
import type {
  HeaderSection,
  HeaderVariant,
  NavLinkRef,
  Section,
  SectionType,
} from "@/types/sections";
import { Button } from "@/components/ui";
import { SECTION_LABELS } from "@/lib/sections";
import { at, el, Glyph, WIDE } from "@/components/ui";

export type HeaderProps = HeaderSection & { sections?: Section[] };

const NOT_IN_NAV: ReadonlySet<SectionType> = new Set([
  "header",
  "footer",
  "hero",
  "cta",
  "promotion",
]);

export function navFor(
  links: NavLinkRef[] | undefined,
  sections: Section[] = [],
): NavLinkRef[] {
  if (links) return links;
  return sections
    .filter((section) => !NOT_IN_NAV.has(section.type))
    .map((section) => ({
      href: `#${section.anchor ?? section.type}`,
      label: SECTION_LABELS[section.type],
    }));
}

export function BrandMark({
  name,
  icon,
  size = "md",
}: Pick<HeaderSection, "name" | "icon"> & { size?: "md" | "lg" }) {
  return (
    <a href="#top" className="flex shrink-0 items-center gap-2.5">
      {icon && (
        <span
          style={{ boxShadow: "var(--sec-shadow)" }}
          className={`flex items-center justify-center rounded-[calc(var(--sec-radius)*0.6)] bg-primary text-primary-foreground ${
            size === "lg" ? "h-11 w-11" : "h-9 w-9"
          }`}
        >
          <Glyph
            icon={icon}
            path="icon"
            size={size === "lg" ? 24 : 20}
            className=""
          />
        </span>
      )}
      <span
        data-role="title"
        style={{
          fontFamily: "var(--font-heading)",
          fontWeight: "var(--sec-heading-weight)",
          letterSpacing: "var(--sec-heading-tracking)",
        }}
        className={size === "lg" ? "text-xl" : "text-lg"}
      >
        {name}
      </span>
    </a>
  );
}

export function NavLinks({
  links,
  field = "links",
  className = "whitespace-nowrap text-sm text-muted-foreground transition-colors hover:text-foreground",
}: {
  links: NavLinkRef[];
  field?: string;
  className?: string;
}) {
  return (
    <>
      {links.map((link, i) => (
        <a
          key={`${link.href}-${i}`}
          href={link.href}
          className={className}
          {...el(`${field}.${i}`, link.label)}
        >
          <span {...at(`${field}.${i}.label`)}>{link.label}</span>
        </a>
      ))}
    </>
  );
}

function MobileNav({
  links,
  button,
}: {
  links: NavLinkRef[];
  button?: HeaderProps["button"];
}) {
  return (
    <details className="group lg:hidden">
      <summary
        aria-label="Menu"
        className="flex h-10 w-10 cursor-pointer list-none items-center justify-center rounded-[calc(var(--sec-radius)*0.5)] text-foreground hover:bg-muted [&::-webkit-details-marker]:hidden"
      >
        <svg
          aria-hidden
          viewBox="0 0 24 24"
          className="h-5 w-5"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
        >
          <path className="group-open:hidden" d="M4 7h16M4 12h16M4 17h16" />
          <path className="hidden group-open:block" d="M6 6l12 12M18 6L6 18" />
        </svg>
      </summary>
      <nav className="absolute inset-x-0 top-full flex flex-col gap-1 border-b border-border bg-background px-6 py-4 shadow-[var(--sec-shadow)] sm:px-8">
        <NavLinks
          links={links}
          className="rounded-[calc(var(--sec-radius)*0.5)] px-3 py-2.5 text-base text-foreground hover:bg-muted"
        />
        {button && (
          <div className="mt-3 sm:hidden">
            <Button button={button} variant="accent" />
          </div>
        )}
      </nav>
    </details>
  );
}

function Bar({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <header
      id="top"
      data-section="header"
      className={`sticky top-0 z-30 w-full border-b border-border bg-background/85 backdrop-blur ${className}`}
    >
      {children}
    </header>
  );
}

function HeaderStandard({ name, icon, links, button, sections }: HeaderProps) {
  const nav = navFor(links, sections);
  return (
    <Bar>
      <div className={`${WIDE} flex h-16 items-center justify-between gap-6`}>
        <BrandMark name={name} icon={icon} />
        {nav.length > 0 && (
          <nav className="hidden items-center gap-6 lg:flex">
            <NavLinks links={nav} />
          </nav>
        )}
        <div className="flex items-center gap-2">
          {button && (
            <div className="hidden shrink-0 sm:block">
              <Button button={button} variant="accent" />
            </div>
          )}
          {nav.length > 0 && <MobileNav links={nav} button={button} />}
        </div>
      </div>
    </Bar>
  );
}

function HeaderCentered({ name, icon, links, button, sections }: HeaderProps) {
  const nav = navFor(links, sections);
  return (
    <Bar>
      <div className={`${WIDE} flex flex-col items-center gap-3 py-4`}>
        <div className="flex w-full items-center justify-between gap-4">
          <span className="hidden flex-1 lg:block" />
          <BrandMark name={name} icon={icon} size="lg" />
          <div className="flex flex-1 items-center justify-end gap-2">
            {button && (
              <div className="hidden sm:block">
                <Button button={button} variant="accent" />
              </div>
            )}
            {nav.length > 0 && <MobileNav links={nav} button={button} />}
          </div>
        </div>
        {nav.length > 0 && (
          <nav className="hidden flex-wrap items-center justify-center gap-6 lg:flex">
            <NavLinks links={nav} />
          </nav>
        )}
      </div>
    </Bar>
  );
}

function HeaderMinimal({ name, icon, button }: HeaderProps) {
  return (
    <Bar>
      <div className={`${WIDE} flex h-16 items-center justify-between gap-6`}>
        <BrandMark name={name} icon={icon} />
        {button && <Button button={button} variant="accent" />}
      </div>
    </Bar>
  );
}

export const HEADER_VARIANTS: Record<
  HeaderVariant,
  ComponentType<HeaderProps>
> = {
  standard: HeaderStandard,
  centered: HeaderCentered,
  minimal: HeaderMinimal,
};

export const Header = HeaderStandard;
