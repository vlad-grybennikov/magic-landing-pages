import { Fragment } from "react";
import type { CSSProperties } from "react";
import type { Section, Theme } from "@/types/sections";
import { themeVars } from "@/lib/theme";
import { packStyleVars } from "@/lib/sections";
import { fontVars } from "@/lib/fonts";
import { SectionRenderer } from "./sections/SectionRenderer";

export function PageRenderer({
  sections,
  theme,
  context,
}: {
  sections: Section[];
  theme?: Theme | null;
  context?: Section[];
}) {
  const vars = {
    ...themeVars(theme),
    ...packStyleVars(theme?.layout),
    ...fontVars(theme?.font),
  } as CSSProperties;

  return (
    <main
      className="flex w-full flex-1 flex-col bg-background font-[family-name:var(--font-body)] text-foreground"
      style={vars}
    >
      {sections.map((section, i) => {
        const view = (
          <SectionRenderer section={section} sections={context ?? sections} />
        );
        return section.anchor && section.anchor !== section.type ? (
          <div key={i} id={section.anchor} className="scroll-mt-16">
            {view}
          </div>
        ) : (
          <Fragment key={i}>{view}</Fragment>
        );
      })}
    </main>
  );
}
