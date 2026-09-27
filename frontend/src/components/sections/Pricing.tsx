import type { ComponentType } from "react";
import type {
  PricingPlan,
  PricingSection,
  PricingVariant,
} from "@/types/sections";
import { Button } from "@/components/ui";
import {
  at,
  el,
  Card,
  CONTENT,
  gridCols,
  Heading,
  Lede,
  PAD,
  SectionHead,
  SectionShell,
  TEXT,
  Tick,
} from "@/components/ui";
import { rich } from "@/lib/richtext";

function Price({
  plan,
  path,
  size = "lg",
}: {
  plan: PricingPlan;
  path: string;
  size?: "md" | "lg";
}) {
  return (
    <p className="flex flex-wrap items-baseline gap-1.5">
      <span
        className={`font-semibold tracking-tight ${
          size === "lg" ? "text-4xl" : "text-3xl"
        }`}
        {...at(`${path}.price`, plan.price)}
      >
        {plan.price}
      </span>
      {plan.period && (
        <span
          {...at(`${path}.period`, plan.period)}
          className="text-sm text-muted-foreground"
        >
          {plan.period}
        </span>
      )}
    </p>
  );
}

function Features({ features, path }: { features: string[]; path: string }) {
  return (
    <ul className="flex flex-col gap-3">
      {features.map((feature, i) => (
        <li key={i} className="flex gap-3 text-sm leading-relaxed">
          <Tick />
          <span
            {...at(`${path}.features.${i}`, feature)}
            className="text-muted-foreground"
          >
            {feature}
          </span>
        </li>
      ))}
    </ul>
  );
}

function FeaturedBadge() {
  return (
    <span className="shrink-0 whitespace-nowrap rounded-full bg-accent px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-accent-foreground">
      Popular
    </span>
  );
}

function PlanName({ plan, path }: { plan: PricingPlan; path: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <h3
        {...at(`${path}.name`, plan.name)}
        className="text-lg font-medium leading-snug"
      >
        {plan.name}
      </h3>
      {plan.featured && <FeaturedBadge />}
    </div>
  );
}

function PlanCard({ plan, path }: { plan: PricingPlan; path: string }) {
  return (
    <Card
      tone={plan.featured ? "plain" : "muted"}
      className={`flex h-full flex-col gap-5 p-7 ${
        plan.featured ? "border-2 border-accent shadow-sm" : ""
      }`}
    >
      <PlanName plan={plan} path={path} />
      <Price plan={plan} path={path} />
      {plan.description && (
        <p
          {...at(`${path}.description`, plan.description)}
          className="text-pretty leading-relaxed text-muted-foreground"
        >
          {rich(plan.description)}
        </p>
      )}
      <Features features={plan.features} path={path} />
      <div className="mt-auto pt-2">
        <Button
          button={plan.button}
          path={`${path}.button`}
          variant={plan.featured ? "accent" : "secondary"}
        />
      </div>
    </Card>
  );
}

function PricingThreeCards({ heading, subhead, plans }: PricingSection) {
  return (
    <SectionShell type="pricing">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div className={`mt-14 grid gap-6 ${gridCols(plans.length)}`}>
          {plans.map((plan, i) => (
            <PlanCard key={i} plan={plan} path={`plans.${i}`} />
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function PricingFeaturedCenter({ heading, subhead, plans }: PricingSection) {
  return (
    <SectionShell type="pricing" tone="muted">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div
          className={`mt-14 grid items-center gap-6 ${gridCols(plans.length)}`}
        >
          {plans.map((plan, i) => (
            <div
              key={i}
              {...el(`plans.${i}`, `Plan ${i + 1}`)}
              className={plan.featured ? "lg:-my-6" : ""}
            >
              <PlanCard plan={plan} path={`plans.${i}`} />
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function PricingTableRows({ heading, subhead, plans }: PricingSection) {
  return (
    <SectionShell type="pricing">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} align="left" />
        <div className="mt-12 divide-y divide-border border-y border-border">
          {plans.map((plan, i) => (
            <div
              key={i}
              {...el(`plans.${i}`, `Plan ${i + 1}`)}
              className="grid gap-6 py-8 lg:grid-cols-[minmax(0,16rem)_1fr_auto] lg:items-center lg:gap-10"
            >
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-3">
                  <h3
                    {...at(`plans.${i}.name`, plan.name)}
                    className="text-lg font-medium"
                  >
                    {plan.name}
                  </h3>
                  {plan.featured && <FeaturedBadge />}
                </div>
                <Price plan={plan} path={`plans.${i}`} size="md" />
              </div>
              <div className="flex flex-col gap-3">
                {plan.description && (
                  <p
                    {...at(`plans.${i}.description`, plan.description)}
                    className="text-pretty leading-relaxed text-muted-foreground"
                  >
                    {rich(plan.description)}
                  </p>
                )}
                <Features features={plan.features} path={`plans.${i}`} />
              </div>
              <Button
                button={plan.button}
                path={`plans.${i}.button`}
                variant={plan.featured ? "accent" : "secondary"}
              />
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function PricingTwoUp({ heading, subhead, plans }: PricingSection) {
  return (
    <SectionShell type="pricing">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div className="mt-14 grid gap-6 sm:grid-cols-2">
          {plans.map((plan, i) => (
            <PlanCard key={i} plan={plan} path={`plans.${i}`} />
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function PricingBorderedColumns({ heading, subhead, plans }: PricingSection) {
  return (
    <SectionShell type="pricing">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div
          className={`mt-14 grid divide-y divide-border overflow-hidden rounded-3xl border border-border sm:divide-x sm:divide-y-0 ${gridCols(
            plans.length,
          )}`}
        >
          {plans.map((plan, i) => (
            <div
              key={i}
              {...el(`plans.${i}`, `Plan ${i + 1}`)}
              className={`flex flex-col gap-5 p-8 ${
                plan.featured ? "bg-primary/5" : ""
              }`}
            >
              <PlanName plan={plan} path={`plans.${i}`} />
              <Price plan={plan} path={`plans.${i}`} />
              {plan.description && (
                <p
                  {...at(`plans.${i}.description`, plan.description)}
                  className="text-pretty leading-relaxed text-muted-foreground"
                >
                  {rich(plan.description)}
                </p>
              )}
              <Features features={plan.features} path={`plans.${i}`} />
              <div className="mt-auto pt-2">
                <Button
                  button={plan.button}
                  path={`plans.${i}.button`}
                  variant={plan.featured ? "accent" : "secondary"}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function PricingSingleOffer({ heading, subhead, plans }: PricingSection) {
  const [plan] = plans;
  const path = "plans.0";
  return (
    <SectionShell type="pricing">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="grid items-center gap-10 rounded-3xl bg-muted p-8 sm:p-12 lg:grid-cols-2 lg:gap-16">
          <div className="flex flex-col items-start gap-4">
            <Heading role="title" size="lg">
              {heading}
            </Heading>
            {subhead && <Lede role="description">{subhead}</Lede>}
            <div className="mt-2 flex flex-col gap-1">
              <span
                {...at(`${path}.name`, plan.name)}
                className="text-sm font-medium text-muted-foreground"
              >
                {plan.name}
              </span>
              <Price plan={plan} path={path} />
            </div>
            <Button button={plan.button} path={path} variant="accent" />
          </div>
          <Card className="p-7">
            {plan.description && (
              <p
                {...at(`${path}.description`, plan.description)}
                className="mb-4 text-pretty leading-relaxed text-muted-foreground"
              >
                {rich(plan.description)}
              </p>
            )}
            <Features features={plan.features} path={path} />
          </Card>
        </div>
      </div>
    </SectionShell>
  );
}

function PricingCompactList({ heading, subhead, plans }: PricingSection) {
  return (
    <SectionShell type="pricing" tone="muted">
      <div className={`${TEXT} ${PAD}`}>
        <SectionHead
          heading={heading}
          subhead={subhead}
          align="left"
          size="md"
        />
        <div className="mt-10 flex flex-col gap-4">
          {plans.map((plan, i) => (
            <Card
              key={i}
              {...el(`plans.${i}`, `Plan ${i + 1}`)}
              className={`flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between ${
                plan.featured ? "border-accent" : ""
              }`}
            >
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center gap-3">
                  <h3
                    {...at(`plans.${i}.name`, plan.name)}
                    className="font-medium"
                  >
                    {plan.name}
                  </h3>
                  {plan.featured && <FeaturedBadge />}
                </div>
                {plan.description && (
                  <p
                    {...at(`plans.${i}.description`, plan.description)}
                    className="text-sm text-muted-foreground"
                  >
                    {rich(plan.description)}
                  </p>
                )}
                <p className="text-sm text-muted-foreground">
                  {plan.features.map((feature, f) => (
                    <span key={f}>
                      {f > 0 && " · "}
                      <span {...at(`plans.${i}.features.${f}`, feature)}>
                        {feature}
                      </span>
                    </span>
                  ))}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-5">
                <Price plan={plan} path={`plans.${i}`} size="md" />
                <Button
                  button={plan.button}
                  path={`plans.${i}.button`}
                  variant={plan.featured ? "accent" : "secondary"}
                />
              </div>
            </Card>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

export const PRICING_VARIANTS: Record<
  PricingVariant,
  ComponentType<PricingSection>
> = {
  "three-cards": PricingThreeCards,
  "featured-center": PricingFeaturedCenter,
  "table-rows": PricingTableRows,
  "two-up": PricingTwoUp,
  "bordered-columns": PricingBorderedColumns,
  "single-offer": PricingSingleOffer,
  "compact-list": PricingCompactList,
};

export const Pricing = PricingThreeCards;
