import type { ComponentType } from "react";
import type {
  FooterSection,
  FooterVariant,
  NavLinkRef,
  Section,
} from "@/types/sections";
import { at, WIDE } from "@/components/ui";
import { BrandMark, NavLinks, navFor } from "./Header";

export type FooterProps = FooterSection & { sections?: Section[] };

function contactsFor(
  contacts: NavLinkRef[] | undefined,
  sections: Section[] = [],
): NavLinkRef[] {
  if (contacts) return contacts;
  const contact = sections.find((section) => section.type === "contact");
  if (contact?.type !== "contact") return [];
  return contact.details.map((detail) => ({
    label: detail.value,
    href: `#${contact.anchor ?? "contact"}`,
  }));
}

function Shell({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <footer
      data-section="footer"
      className={`w-full border-t border-border bg-muted ${className}`}
    >
      {children}
    </footer>
  );
}

function Copyright({ name, text }: { name: string; text?: string | null }) {
  const line = text ?? `© ${new Date().getFullYear()} ${name}`;
  return (
    <span {...at("copyright", line)} className="text-sm text-muted-foreground">
      {line}
    </span>
  );
}

function ColumnHeading({
  path,
  fallback,
  text,
}: {
  path: string;
  fallback: string;
  text?: string | null;
}) {
  const line = text ?? fallback;
  return (
    <span
      {...at(path, line)}
      className="text-xs font-semibold uppercase tracking-[0.14em] text-foreground"
    >
      {line}
    </span>
  );
}

function FooterColumns({
  name,
  icon,
  links,
  tagline,
  links_label,
  contacts_label,
  contacts,
  copyright,
  sections,
}: FooterProps) {
  const nav = navFor(links, sections);
  const reach = contactsFor(contacts, sections);

  return (
    <Shell>
      <div className={`${WIDE} flex flex-col gap-10 py-14`}>
        <div className="flex flex-col justify-between gap-10 lg:flex-row">
          <div className="flex max-w-sm flex-col gap-3">
            <BrandMark name={name} icon={icon} />
            {tagline && (
              <p
                data-role="description"
                className="text-sm leading-relaxed text-muted-foreground"
              >
                {tagline}
              </p>
            )}
          </div>

          <div className="flex flex-col gap-10 sm:flex-row sm:gap-16">
            {nav.length > 0 && (
              <nav className="flex flex-col gap-2.5">
                <ColumnHeading
                  path="links_label"
                  fallback="Page"
                  text={links_label}
                />
                <NavLinks
                  links={nav}
                  className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                />
              </nav>
            )}

            {reach.length > 0 && (
              <nav className="flex flex-col gap-2.5">
                <ColumnHeading
                  path="contacts_label"
                  fallback="Get in touch"
                  text={contacts_label}
                />
                <NavLinks
                  links={reach}
                  field="contacts"
                  className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                />
              </nav>
            )}
          </div>
        </div>

        <div className="border-t border-border pt-6">
          <Copyright name={name} text={copyright} />
        </div>
      </div>
    </Shell>
  );
}

function FooterSimple({
  name,
  icon,
  links,
  tagline,
  copyright,
  sections,
}: FooterProps) {
  const nav = navFor(links, sections);
  return (
    <Shell>
      <div
        className={`${WIDE} flex flex-col gap-6 py-10 lg:flex-row lg:items-center lg:justify-between`}
      >
        <div className="flex flex-col gap-2">
          <BrandMark name={name} icon={icon} />
          {tagline && (
            <p
              data-role="description"
              className="text-sm leading-relaxed text-muted-foreground"
            >
              {tagline}
            </p>
          )}
        </div>
        {nav.length > 0 && (
          <nav className="flex flex-wrap gap-x-6 gap-y-2">
            <NavLinks
              links={nav}
              className="text-sm text-muted-foreground transition-colors hover:text-foreground"
            />
          </nav>
        )}
        <Copyright name={name} text={copyright} />
      </div>
    </Shell>
  );
}

function FooterCentered({
  name,
  icon,
  links,
  tagline,
  copyright,
  sections,
}: FooterProps) {
  const nav = navFor(links, sections);
  return (
    <Shell>
      <div
        className={`${WIDE} flex flex-col items-center gap-6 py-14 text-center`}
      >
        <BrandMark name={name} icon={icon} size="lg" />
        {tagline && (
          <p
            data-role="description"
            className="max-w-md text-sm leading-relaxed text-muted-foreground"
          >
            {tagline}
          </p>
        )}
        {nav.length > 0 && (
          <nav className="flex flex-wrap justify-center gap-x-6 gap-y-2">
            <NavLinks
              links={nav}
              className="text-sm text-muted-foreground transition-colors hover:text-foreground"
            />
          </nav>
        )}
        <div className="w-full border-t border-border pt-6">
          <Copyright name={name} text={copyright} />
        </div>
      </div>
    </Shell>
  );
}

export const FOOTER_VARIANTS: Record<
  FooterVariant,
  ComponentType<FooterProps>
> = {
  columns: FooterColumns,
  simple: FooterSimple,
  centered: FooterCentered,
};

export const Footer = FooterColumns;
