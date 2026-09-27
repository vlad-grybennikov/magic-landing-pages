import type { ComponentType } from "react";
import type { FAQItem, FAQSection, FaqVariant } from "@/types/sections";
import {
  at,
  Card,
  el,
  CONTENT,
  Heading,
  Lede,
  Numeral,
  PAD,
  SectionHead,
  SectionShell,
  TEXT,
} from "@/components/ui";
import { rich } from "@/lib/richtext";

function Disclosure({
  item,
  path,
  label,
  className = "",
}: {
  item: FAQItem;
  path: string;
  label: string;
  className?: string;
}) {
  return (
    <details {...el(path, label)} className={`group ${className}`}>
      <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-lg font-medium">
        <span
          {...at(`${path}.question`, item.question)}
          className="text-pretty"
        >
          {rich(item.question)}
        </span>
        <span
          aria-hidden
          className="text-2xl leading-none text-muted-foreground transition-transform group-open:rotate-45"
        >
          +
        </span>
      </summary>
      <p
        {...at(`${path}.answer`, item.answer)}
        className="mt-3 text-pretty leading-relaxed text-muted-foreground"
      >
        {rich(item.answer)}
      </p>
    </details>
  );
}

function Pair({
  item,
  path,
  label,
}: {
  item: FAQItem;
  path: string;
  label: string;
}) {
  return (
    <div {...el(path, label)} className="flex flex-col gap-2">
      <h3
        {...at(`${path}.question`, item.question)}
        className="text-pretty text-lg font-medium"
      >
        {rich(item.question)}
      </h3>
      <p
        {...at(`${path}.answer`, item.answer)}
        className="text-pretty leading-relaxed text-muted-foreground"
      >
        {rich(item.answer)}
      </p>
    </div>
  );
}

function FaqAccordion({ heading, subhead, items }: FAQSection) {
  return (
    <SectionShell type="faq">
      <div className={`${TEXT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} align="left" />
        <div className="mt-10 border-y border-border">
          {items.map((item, i) => (
            <Disclosure
              key={i}
              item={item}
              path={`items.${i}`}
              label={`Question ${i + 1}`}
              className="border-b border-border py-5 last:border-b-0"
            />
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function FaqAccordionBoxed({ heading, subhead, items }: FAQSection) {
  return (
    <SectionShell type="faq" tone="muted">
      <div className={`${TEXT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div className="mt-10 flex flex-col gap-4">
          {items.map((item, i) => (
            <Card key={i}>
              <Disclosure
                item={item}
                path={`items.${i}`}
                label={`Question ${i + 1}`}
                className="p-6"
              />
            </Card>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function FaqTwoColumnStatic({ heading, subhead, items }: FAQSection) {
  return (
    <SectionShell type="faq">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div className="mt-14 grid gap-x-14 gap-y-10 sm:grid-cols-2">
          {items.map((item, i) => (
            <Pair
              key={i}
              item={item}
              path={`items.${i}`}
              label={`Question ${i + 1}`}
            />
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function FaqHeadingLeft({ heading, subhead, items }: FAQSection) {
  return (
    <SectionShell type="faq">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="grid gap-10 lg:grid-cols-[minmax(0,22rem)_1fr] lg:gap-20">
          <div className="flex flex-col gap-4 lg:sticky lg:top-16 lg:self-start">
            <Heading role="title" size="lg">
              {heading ?? "Questions"}
            </Heading>
            {subhead && <Lede role="description">{subhead}</Lede>}
          </div>
          <div className="border-t border-border">
            {items.map((item, i) => (
              <Disclosure
                key={i}
                item={item}
                path={`items.${i}`}
                label={`Question ${i + 1}`}
                className="border-b border-border py-5"
              />
            ))}
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function FaqNumberedList({ heading, subhead, items }: FAQSection) {
  return (
    <SectionShell type="faq">
      <div className={`${TEXT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} align="left" />
        <ol className="mt-10 flex flex-col gap-8">
          {items.map((item, i) => (
            <li key={i} className="flex gap-5">
              <Numeral n={i + 1} />
              <Pair
                item={item}
                path={`items.${i}`}
                label={`Question ${i + 1}`}
              />
            </li>
          ))}
        </ol>
      </div>
    </SectionShell>
  );
}

function FaqTintedAccordion({ heading, subhead, items }: FAQSection) {
  return (
    <SectionShell type="faq">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="rounded-3xl bg-primary/5 p-8 sm:p-12">
          <SectionHead heading={heading} subhead={subhead} />
          <div className="mx-auto mt-10 max-w-2xl divide-y divide-primary/15 border-y border-primary/15">
            {items.map((item, i) => (
              <Disclosure
                key={i}
                item={item}
                path={`items.${i}`}
                label={`Question ${i + 1}`}
                className="py-5"
              />
            ))}
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function FaqCompactPairs({ heading, subhead, items }: FAQSection) {
  return (
    <SectionShell type="faq" tone="muted">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead
          heading={heading}
          subhead={subhead}
          align="left"
          size="md"
        />
        <dl className="mt-10 divide-y divide-border border-t border-border">
          {items.map((item, i) => (
            <div
              key={i}
              className="grid gap-2 py-6 sm:grid-cols-[minmax(0,18rem)_1fr] sm:gap-10"
            >
              <dt
                {...at(`items.${i}.question`, item.question)}
                className="text-pretty font-medium"
              >
                {rich(item.question)}
              </dt>
              <dd
                {...at(`items.${i}.answer`, item.answer)}
                className="text-pretty leading-relaxed text-muted-foreground"
              >
                {rich(item.answer)}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </SectionShell>
  );
}

export const FAQ_VARIANTS: Record<FaqVariant, ComponentType<FAQSection>> = {
  accordion: FaqAccordion,
  "accordion-boxed": FaqAccordionBoxed,
  "two-column-static": FaqTwoColumnStatic,
  "heading-left": FaqHeadingLeft,
  "numbered-list": FaqNumberedList,
  "tinted-accordion": FaqTintedAccordion,
  "compact-pairs": FaqCompactPairs,
};

export const Faq = FaqAccordion;
