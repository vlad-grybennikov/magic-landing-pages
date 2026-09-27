import type { ComponentType } from "react";
import type {
  TestimonialItem,
  TestimonialsSection,
  TestimonialsVariant,
} from "@/types/sections";
import {
  at,
  el,
  Card,
  CONTENT,
  gridCols,
  Heading,
  Lede,
  PAD,
  QuoteMark,
  Rail,
  SectionHead,
  SectionShell,
  Stars,
  TEXT,
} from "@/components/ui";
import { rich } from "@/lib/richtext";

function Quote({
  item,
  path,
  size = "md",
}: {
  item: TestimonialItem;
  path: string;
  size?: "md" | "lg";
}) {
  return (
    <blockquote
      {...at(`${path}.content`, item.content)}
      className={`text-pretty text-muted-foreground ${
        size === "lg"
          ? "text-xl leading-relaxed sm:text-2xl"
          : "leading-relaxed"
      }`}
    >
      {rich(item.content)}
    </blockquote>
  );
}

function Attribution({ item, path }: { item: TestimonialItem; path: string }) {
  return (
    <figcaption
      {...at(`${path}.name`, item.name)}
      className="font-medium text-primary"
    >
      {item.name}
    </figcaption>
  );
}

function TestimonialsCardsGrid({
  heading,
  subhead,
  items,
}: TestimonialsSection) {
  return (
    <SectionShell type="testimonials">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div
          className={`mt-14 grid gap-6 ${
            items.length === 1 ? "" : gridCols(Math.min(items.length, 3))
          }`}
        >
          {items.map((item, i) => (
            <Card
              key={i}
              {...el(`items.${i}`, `Testimonial ${i + 1}`)}
              tone="muted"
              className="p-7"
            >
              <figure className="flex h-full flex-col gap-4">
                <Stars rating={item.rating} path={`items.${i}.rating`} />
                <Quote item={item} path={`items.${i}`} />
                <div className="mt-auto pt-2">
                  <Attribution item={item} path={`items.${i}`} />
                </div>
              </figure>
            </Card>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function TestimonialsSingleQuote({ heading, items }: TestimonialsSection) {
  const [lead, ...rest] = items;
  return (
    <SectionShell type="testimonials" tone="muted">
      <div className={`${PAD}`}>
        <figure className={`${TEXT} flex flex-col items-center text-center`}>
          {heading && (
            <Heading
              role="title"
              size="sm"
              className="mb-6 text-muted-foreground"
            >
              {heading}
            </Heading>
          )}
          <QuoteMark />
          <Quote item={lead} path="items.0" size="lg" />
          <div className="mt-6 flex flex-col items-center gap-2">
            <Stars rating={lead.rating} path="items.0.rating" />
            <Attribution item={lead} path="items.0" />
          </div>
        </figure>

        {rest.length > 0 && (
          <div
            className={`${CONTENT} mt-14 grid gap-6 border-t border-border pt-10 ${gridCols(rest.length)}`}
          >
            {rest.map((item, i) => (
              <figure
                key={i}
                {...el(`items.${i + 1}`, `Testimonial ${i + 2}`)}
                className="flex flex-col gap-2"
              >
                <Stars
                  rating={item.rating}
                  path={`items.${i + 1}.rating`}
                  size="sm"
                />
                <Quote item={item} path={`items.${i + 1}`} />
                <Attribution item={item} path={`items.${i + 1}`} />
              </figure>
            ))}
          </div>
        )}
      </div>
    </SectionShell>
  );
}

function TestimonialsQuoteRail({
  heading,
  subhead,
  items,
}: TestimonialsSection) {
  return (
    <SectionShell type="testimonials">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} align="left" />
        <Rail className="mt-12">
          {items.map((item, i) => (
            <Card
              key={i}
              {...el(`items.${i}`, `Testimonial ${i + 1}`)}
              className="w-[19rem] shrink-0 snap-start p-7 sm:w-[22rem]"
            >
              <figure className="flex h-full flex-col gap-4">
                <Stars rating={item.rating} path={`items.${i}.rating`} />
                <Quote item={item} path={`items.${i}`} />
                <div className="mt-auto pt-2">
                  <Attribution item={item} path={`items.${i}`} />
                </div>
              </figure>
            </Card>
          ))}
        </Rail>
      </div>
    </SectionShell>
  );
}

function TestimonialsTwoColumnLarge({
  heading,
  subhead,
  items,
}: TestimonialsSection) {
  return (
    <SectionShell type="testimonials">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div className="mt-14 grid gap-x-16 gap-y-12 sm:grid-cols-2">
          {items.map((item, i) => (
            <figure
              key={i}
              {...el(`items.${i}`, `Testimonial ${i + 1}`)}
              className="flex flex-col gap-4"
            >
              <QuoteMark className="text-5xl" />
              <Quote item={item} path={`items.${i}`} />
              <div className="flex items-center gap-3">
                <Attribution item={item} path={`items.${i}`} />
                <Stars
                  rating={item.rating}
                  path={`items.${i}.rating`}
                  size="sm"
                />
              </div>
            </figure>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function TestimonialsBorderedList({
  heading,
  subhead,
  items,
}: TestimonialsSection) {
  return (
    <SectionShell type="testimonials">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} align="left" />
        <div className="mt-12 divide-y divide-border border-y border-border">
          {items.map((item, i) => (
            <figure
              key={i}
              {...el(`items.${i}`, `Testimonial ${i + 1}`)}
              className="grid gap-3 py-8 sm:grid-cols-[minmax(0,12rem)_1fr] sm:gap-10"
            >
              <div className="flex flex-col gap-1.5">
                <Attribution item={item} path={`items.${i}`} />
                <Stars
                  rating={item.rating}
                  path={`items.${i}.rating`}
                  size="sm"
                />
              </div>
              <Quote item={item} path={`items.${i}`} />
            </figure>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function TestimonialsTintedCards({
  heading,
  subhead,
  items,
}: TestimonialsSection) {
  return (
    <SectionShell type="testimonials" tone="tinted">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div
          className={`mt-14 grid gap-6 ${gridCols(Math.min(items.length, 3))}`}
        >
          {items.map((item, i) => (
            <Card
              key={i}
              {...el(`items.${i}`, `Testimonial ${i + 1}`)}
              className="p-7"
            >
              <figure className="flex h-full flex-col gap-4">
                <QuoteMark className="text-4xl" />
                <Quote item={item} path={`items.${i}`} />
                <div className="mt-auto flex flex-col gap-1.5 pt-2">
                  <Attribution item={item} path={`items.${i}`} />
                  <Stars
                    rating={item.rating}
                    path={`items.${i}.rating`}
                    size="sm"
                  />
                </div>
              </figure>
            </Card>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function TestimonialsMasonryQuotes({
  heading,
  subhead,
  items,
}: TestimonialsSection) {
  return (
    <SectionShell type="testimonials" tone="muted">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div className="mt-14 gap-6 sm:columns-2 lg:columns-3">
          {items.map((item, i) => (
            <Card
              key={i}
              {...el(`items.${i}`, `Testimonial ${i + 1}`)}
              className="mb-6 break-inside-avoid p-6"
            >
              <figure className="flex flex-col gap-3">
                <Stars
                  rating={item.rating}
                  path={`items.${i}.rating`}
                  size="sm"
                />
                <Quote item={item} path={`items.${i}`} />
                <Attribution item={item} path={`items.${i}`} />
              </figure>
            </Card>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function TestimonialsRatingSummary({
  heading,
  subhead,
  items,
}: TestimonialsSection) {
  const average =
    items.reduce((total, item) => total + item.rating, 0) / items.length;

  return (
    <SectionShell type="testimonials">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="grid gap-12 lg:grid-cols-[minmax(0,18rem)_1fr] lg:gap-16">
          <div className="flex flex-col gap-4 lg:sticky lg:top-16 lg:self-start">
            {heading && (
              <Heading role="title" size="md">
                {heading}
              </Heading>
            )}
            <div className="flex flex-col gap-2 rounded-2xl bg-muted p-6">
              <span className="text-5xl font-semibold tabular-nums text-primary">
                {average.toFixed(1)}
              </span>
              <Stars rating={average} size="lg" />
              <span className="text-sm text-muted-foreground">
                from {items.length} {items.length === 1 ? "review" : "reviews"}
              </span>
            </div>
            {subhead && (
              <Lede role="description" className="text-base">
                {subhead}
              </Lede>
            )}
          </div>

          <div className="flex flex-col divide-y divide-border">
            {items.map((item, i) => (
              <figure
                key={i}
                {...el(`items.${i}`, `Testimonial ${i + 1}`)}
                className="flex flex-col gap-3 py-6 first:pt-0"
              >
                <div className="flex items-center justify-between gap-4">
                  <Attribution item={item} path={`items.${i}`} />
                  <Stars
                    rating={item.rating}
                    path={`items.${i}.rating`}
                    size="sm"
                  />
                </div>
                <Quote item={item} path={`items.${i}`} />
              </figure>
            ))}
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

export const TESTIMONIALS_VARIANTS: Record<
  TestimonialsVariant,
  ComponentType<TestimonialsSection>
> = {
  "cards-grid": TestimonialsCardsGrid,
  "single-quote": TestimonialsSingleQuote,
  "quote-rail": TestimonialsQuoteRail,
  "two-column-large": TestimonialsTwoColumnLarge,
  "bordered-list": TestimonialsBorderedList,
  "tinted-cards": TestimonialsTintedCards,
  "masonry-quotes": TestimonialsMasonryQuotes,
  "rating-summary": TestimonialsRatingSummary,
};

export const Testimonials = TestimonialsCardsGrid;
