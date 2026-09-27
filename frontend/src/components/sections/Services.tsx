import type { ComponentType } from "react";
import type {
  ServiceItem,
  ServicesSection,
  ServicesVariant,
} from "@/types/sections";
import {
  at,
  el,
  Card,
  CONTENT,
  gridCols,
  PAD,
  Photo,
  Rail,
  Scrim,
  SectionHead,
  SectionShell,
  WIDE,
} from "@/components/ui";
import { rich } from "@/lib/richtext";

const CARD_SIZE = "(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw";
const HALF = "(max-width: 1024px) 100vw, 50vw";

function ItemBody({
  item,
  path,
  large = false,
  className = "",
}: {
  item: ServiceItem;
  path: string;
  large?: boolean;
  className?: string;
}) {
  return (
    <div className={`flex flex-col items-start gap-2 ${className}`}>
      <h3
        {...at(`${path}.title`, item.title)}
        className={
          large
            ? "text-2xl font-semibold tracking-tight"
            : "text-lg font-medium"
        }
      >
        {rich(item.title)}
      </h3>
      <p
        {...at(`${path}.caption`, item.caption)}
        className={`text-pretty leading-relaxed text-muted-foreground ${
          large ? "text-lg" : ""
        }`}
      >
        {rich(item.caption)}
      </p>
      {item.button && (
        <a
          href={item.button.href ?? "#"}
          className="mt-1 text-sm font-medium text-primary underline decoration-primary/30 underline-offset-4 hover:decoration-primary"
        >
          <span {...at(`${path}.button.label`, item.button.label)}>
            {item.button.label}
          </span>
        </a>
      )}
    </div>
  );
}

function ServicesPhotoCards({ heading, subhead, items }: ServicesSection) {
  return (
    <SectionShell type="services">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div className={`mt-14 grid gap-6 ${gridCols(items.length)}`}>
          {items.map((item, i) => (
            <Card
              key={i}
              {...el(`items.${i}`, `Service ${i + 1}`)}
              className="overflow-hidden"
            >
              <Photo
                image={item.image}
                path={`items.${i}.image`}
                ratio="16/10"
                rounded="none"
                sizes={CARD_SIZE}
              />
              <ItemBody item={item} path={`items.${i}`} className="p-6" />
            </Card>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function ServicesPhotoRows({ heading, subhead, items }: ServicesSection) {
  return (
    <SectionShell type="services">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} align="left" />
        <div className="mt-12 flex flex-col gap-12">
          {items.map((item, i) => (
            <div
              key={i}
              className="grid items-center gap-8 lg:grid-cols-[minmax(0,26rem)_1fr] lg:gap-14"
            >
              <Photo
                image={item.image}
                path={`items.${i}.image`}
                ratio="3/2"
                rounded="2xl"
                sizes={HALF}
                className={i % 2 === 1 ? "lg:order-2" : ""}
              />
              <div className={i % 2 === 1 ? "lg:order-1" : ""}>
                <ItemBody item={item} path={`items.${i}`} large />
              </div>
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function ServicesOverlayTiles({ heading, subhead, items }: ServicesSection) {
  return (
    <SectionShell type="services">
      <div className={`${WIDE} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div className={`mt-14 grid gap-5 ${gridCols(items.length)}`}>
          {items.map((item, i) => (
            <Photo
              key={i}
              image={item.image}
              path={`items.${i}.image`}
              ratio="3/4"
              rounded="2xl"
              sizes={CARD_SIZE}
            >
              <Scrim strength="lg" />
              <div
                {...el(`items.${i}`, `Service ${i + 1}`)}
                className="absolute inset-0 flex flex-col justify-end gap-2 p-6"
              >
                <h3
                  {...at(`items.${i}.title`, item.title)}
                  className="text-lg font-medium text-white"
                >
                  {rich(item.title)}
                </h3>
                <p
                  {...at(`items.${i}.caption`, item.caption)}
                  className="text-pretty text-sm leading-relaxed text-white/85"
                >
                  {rich(item.caption)}
                </p>
                {item.button && (
                  <a
                    href={item.button.href ?? "#"}
                    className="mt-1 text-sm font-medium text-white underline decoration-white/40 underline-offset-4 hover:decoration-white"
                  >
                    <span {...at(`items.${i}.button.label`, item.button.label)}>
                      {item.button.label}
                    </span>
                  </a>
                )}
              </div>
            </Photo>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function ServicesListWithThumbs({ heading, subhead, items }: ServicesSection) {
  return (
    <SectionShell type="services" tone="muted">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} align="left" />
        <div className="mt-12 divide-y divide-border border-y border-border">
          {items.map((item, i) => (
            <div
              key={i}
              {...el(`items.${i}`, `Service ${i + 1}`)}
              className="grid items-center gap-5 py-6 sm:grid-cols-[7rem_1fr] sm:gap-8"
            >
              <Photo
                image={item.image}
                path={`items.${i}.image`}
                ratio="1/1"
                rounded="xl"
                sizes="112px"
                className="max-w-28"
              />
              <ItemBody item={item} path={`items.${i}`} />
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function ServicesFeatureFirst({ heading, subhead, items }: ServicesSection) {
  const [lead, ...rest] = items;
  return (
    <SectionShell type="services">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} align="left" />

        <div className="mt-12 grid items-center gap-8 rounded-3xl bg-muted p-6 lg:grid-cols-2 lg:gap-14 lg:p-10">
          <Photo
            image={lead.image}
            path="items.0.image"
            ratio="4/3"
            rounded="2xl"
            sizes={HALF}
          />
          <div
            {...el("items.0", "Service 1")}
            className="flex flex-col items-start gap-3"
          >
            <ItemBody item={lead} path="items.0" large />
          </div>
        </div>

        {rest.length > 0 && (
          <div className={`mt-8 grid gap-6 ${gridCols(rest.length)}`}>
            {rest.map((item, i) => (
              <div
                key={i}
                {...el(`items.${i + 1}`, `Service ${i + 2}`)}
                className="flex flex-col gap-4"
              >
                <Photo
                  image={item.image}
                  path={`items.${i}.image`}
                  ratio="16/10"
                  rounded="2xl"
                  sizes={CARD_SIZE}
                />
                <ItemBody item={item} path={`items.${i + 1}`} />
              </div>
            ))}
          </div>
        )}
      </div>
    </SectionShell>
  );
}

function ServicesBorderedGrid({ heading, subhead, items }: ServicesSection) {
  return (
    <SectionShell type="services">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div className="mt-14 grid overflow-hidden rounded-3xl border border-border sm:grid-cols-2">
          {items.map((item, i) => (
            <div
              key={i}
              {...el(`items.${i}`, `Service ${i + 1}`)}
              className="flex flex-col gap-4 border-b border-border p-8 last:border-b-0 sm:[&:nth-child(odd)]:border-r sm:[&:nth-last-child(2):nth-child(odd)]:border-b-0"
            >
              <Photo
                image={item.image}
                path={`items.${i}.image`}
                ratio="16/9"
                rounded="xl"
                sizes={HALF}
                className="max-w-24"
              />
              <ItemBody item={item} path={`items.${i}`} />
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function ServicesRail({ heading, subhead, items }: ServicesSection) {
  return (
    <SectionShell type="services">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} align="left" />
        <Rail className="mt-12">
          {items.map((item, i) => (
            <Card
              key={i}
              {...el(`items.${i}`, `Service ${i + 1}`)}
              className="w-[17rem] shrink-0 snap-start overflow-hidden sm:w-[20rem]"
            >
              <Photo
                image={item.image}
                path={`items.${i}.image`}
                ratio="4/3"
                rounded="none"
                sizes="320px"
              />
              <ItemBody item={item} path={`items.${i}`} className="p-6" />
            </Card>
          ))}
        </Rail>
      </div>
    </SectionShell>
  );
}

export const SERVICES_VARIANTS: Record<
  ServicesVariant,
  ComponentType<ServicesSection>
> = {
  "photo-cards": ServicesPhotoCards,
  "photo-rows": ServicesPhotoRows,
  "overlay-tiles": ServicesOverlayTiles,
  "list-with-thumbs": ServicesListWithThumbs,
  "feature-first": ServicesFeatureFirst,
  "bordered-grid": ServicesBorderedGrid,
  rail: ServicesRail,
};

export const Services = ServicesPhotoCards;
