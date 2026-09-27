import type { ComponentType } from "react";
import type {
  ContactDetail,
  ContactSection,
  ContactVariant,
} from "@/types/sections";
import { Button } from "@/components/ui";
import {
  at,
  el,
  Card,
  CONTENT,
  Glyph,
  GlyphTile,
  gridCols,
  Heading,
  Lede,
  PAD,
  PAD_TIGHT,
  Photo,
  SectionHead,
  SectionShell,
  TEXT,
} from "@/components/ui";

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE = /^[+(]?[\d][\d\s().-]{6,}$/;

function hrefFor(value: string): string | null {
  const text = value.trim();
  if (EMAIL.test(text)) return `mailto:${text}`;
  if (PHONE.test(text)) return `tel:${text.replace(/[\s().-]/g, "")}`;
  if (/^https?:\/\//i.test(text)) return text;
  return null;
}

function DetailValue({ detail }: { detail: ContactDetail }) {
  const href = hrefFor(detail.value);
  if (!href) {
    return <span className="text-pretty">{detail.value}</span>;
  }
  return (
    <a
      href={href}
      className="text-pretty underline decoration-border underline-offset-4 hover:decoration-primary"
    >
      {detail.value}
    </a>
  );
}

function Detail({ detail, path }: { detail: ContactDetail; path: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span
        {...at(`${path}.label`, detail.label)}
        className="text-sm text-muted-foreground"
      >
        {detail.label}
      </span>
      <span {...at(`${path}.value`, detail.value)} className="font-medium">
        <DetailValue detail={detail} />
      </span>
    </div>
  );
}

function DetailRow({ detail, path }: { detail: ContactDetail; path: string }) {
  return (
    <div className="flex items-start gap-3">
      <Glyph
        icon={detail.icon}
        path={`${path}.icon`}
        size={20}
        className="mt-0.5 text-primary"
      />
      <div className="flex flex-col gap-0.5">
        <span
          {...at(`${path}.label`, detail.label)}
          className="text-sm text-muted-foreground"
        >
          {detail.label}
        </span>
        <span {...at(`${path}.value`, detail.value)} className="font-medium">
          <DetailValue detail={detail} />
        </span>
      </div>
    </div>
  );
}

function ContactDetailsAndCta({
  heading,
  description,
  details,
  button,
}: ContactSection) {
  return (
    <SectionShell type="contact" tone="muted">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="grid gap-10 lg:grid-cols-2 lg:gap-20">
          <div className="flex flex-col gap-5">
            <Heading role="title" size="lg">
              {heading}
            </Heading>
            {description && <Lede role="description">{description}</Lede>}
            {button && (
              <div className="mt-2">
                <Button button={button} variant="accent" />
              </div>
            )}
          </div>
          <div className="flex flex-col gap-6">
            {details.map((detail, i) => (
              <DetailRow key={i} detail={detail} path={`details.${i}`} />
            ))}
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function ContactCenteredDetails({
  heading,
  description,
  details,
  button,
}: ContactSection) {
  return (
    <SectionShell type="contact">
      <div className={`${TEXT} ${PAD}`}>
        <SectionHead heading={heading} subhead={description} />
        <div className="mt-10 flex flex-wrap justify-center gap-x-12 gap-y-6 text-center">
          {details.map((detail, i) => (
            <Detail key={i} detail={detail} path={`details.${i}`} />
          ))}
        </div>
        {button && (
          <div className="mt-10 flex justify-center">
            <Button button={button} variant="accent" />
          </div>
        )}
      </div>
    </SectionShell>
  );
}

function ContactCards({
  heading,
  description,
  details,
  button,
}: ContactSection) {
  return (
    <SectionShell type="contact">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={description} />
        <div className={`mt-14 grid gap-6 ${gridCols(details.length)}`}>
          {details.map((detail, i) => (
            <Card
              key={i}
              {...el(`details.${i}`, `Detail ${i + 1}`)}
              className="flex flex-col gap-4 p-7"
            >
              <GlyphTile
                icon={detail.icon}
                path={`details.${i}.icon`}
                shape="rounded"
              />
              <Detail detail={detail} path={`details.${i}`} />
            </Card>
          ))}
        </div>
        {button && (
          <div className="mt-12 flex justify-center">
            <Button button={button} variant="accent" />
          </div>
        )}
      </div>
    </SectionShell>
  );
}

function ContactWithPhoto(section: ContactSection) {
  const { heading, description, details, button, image } = section;
  if (!image) return <ContactDetailsAndCta {...section} />;

  return (
    <SectionShell type="contact">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="grid items-center gap-10 lg:grid-cols-2 lg:gap-16">
          <Photo
            image={image}
            path="image"
            ratio="4/3"
            rounded="3xl"
            sizes="(max-width: 1024px) 100vw, 50vw"
          />
          <div className="flex flex-col gap-6">
            <div className="flex flex-col gap-4">
              <Heading role="title" size="lg">
                {heading}
              </Heading>
              {description && <Lede role="description">{description}</Lede>}
            </div>
            <div className="flex flex-col gap-5 border-t border-border pt-6">
              {details.map((detail, i) => (
                <DetailRow key={i} detail={detail} path={`details.${i}`} />
              ))}
            </div>
            {button && <Button button={button} variant="accent" />}
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function ContactInlineRow({ heading, details, button }: ContactSection) {
  return (
    <SectionShell type="contact" tone="tinted">
      <div className={`${CONTENT} ${PAD_TIGHT}`}>
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:gap-10">
            <Heading role="title" size="sm">
              {heading}
            </Heading>
            <div className="flex flex-wrap gap-x-8 gap-y-3">
              {details.map((detail, i) => (
                <Detail key={i} detail={detail} path={`details.${i}`} />
              ))}
            </div>
          </div>
          {button && (
            <div className="shrink-0">
              <Button button={button} variant="accent" />
            </div>
          )}
        </div>
      </div>
    </SectionShell>
  );
}

function ContactBoxed({
  heading,
  description,
  details,
  button,
}: ContactSection) {
  return (
    <SectionShell type="contact">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="rounded-3xl border border-border p-8 sm:p-12">
          <div className="grid gap-10 lg:grid-cols-[1fr_auto] lg:items-end">
            <div className="flex flex-col gap-4">
              <Heading role="title" size="lg">
                {heading}
              </Heading>
              {description && (
                <Lede role="description" className="max-w-xl">
                  {description}
                </Lede>
              )}
            </div>
            {button && <Button button={button} variant="accent" />}
          </div>
          <div className="mt-10 grid gap-6 border-t border-border pt-8 sm:grid-cols-2 lg:grid-cols-3">
            {details.map((detail, i) => (
              <DetailRow key={i} detail={detail} path={`details.${i}`} />
            ))}
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function ContactTwoColumnList({
  heading,
  description,
  details,
  button,
}: ContactSection) {
  return (
    <SectionShell type="contact">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="grid gap-10 lg:grid-cols-[minmax(0,22rem)_1fr] lg:gap-20">
          <div className="flex flex-col gap-4">
            <Heading role="title" size="lg">
              {heading}
            </Heading>
            {description && <Lede role="description">{description}</Lede>}
            {button && (
              <div className="mt-2">
                <Button button={button} variant="accent" />
              </div>
            )}
          </div>
          <dl className="divide-y divide-border border-y border-border">
            {details.map((detail, i) => (
              <div
                key={i}
                {...el(`details.${i}`, `Detail ${i + 1}`)}
                className="grid gap-1 py-5 sm:grid-cols-[minmax(0,10rem)_1fr] sm:gap-6"
              >
                <dt
                  {...at(`details.${i}.label`, detail.label)}
                  className="text-sm text-muted-foreground"
                >
                  {detail.label}
                </dt>
                <dd
                  {...at(`details.${i}.value`, detail.value)}
                  className="font-medium"
                >
                  <DetailValue detail={detail} />
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </SectionShell>
  );
}

export const CONTACT_VARIANTS: Record<
  ContactVariant,
  ComponentType<ContactSection>
> = {
  "details-and-cta": ContactDetailsAndCta,
  "centered-details": ContactCenteredDetails,
  cards: ContactCards,
  "with-photo": ContactWithPhoto,
  "inline-row": ContactInlineRow,
  boxed: ContactBoxed,
  "two-column-list": ContactTwoColumnList,
};

export const Contact = ContactDetailsAndCta;
