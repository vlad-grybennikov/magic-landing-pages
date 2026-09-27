import type { ComponentType, ReactNode } from "react";
import type { TeamMember, TeamSection, TeamVariant } from "@/types/sections";
import {
  at,
  el,
  Card,
  CONTENT,
  gridCols,
  PAD,
  Photo,
  Scrim,
  SectionHead,
  SectionShell,
  WIDE,
} from "@/components/ui";
import { rich } from "@/lib/richtext";

const CARD_SIZE = "(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw";
const HALF = "(max-width: 768px) 100vw, 50vw";

function initialsOf(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? "")
    .join("");
}

function Avatar({
  member,
  path,
  ratio = "1/1",
  rounded = "full",
  sizes,
  className = "",
  children,
}: {
  member: TeamMember;
  path?: string;
  ratio?: string;
  rounded?: "none" | "lg" | "xl" | "2xl" | "3xl" | "full";
  sizes?: string;
  className?: string;
  children?: ReactNode;
}) {
  if (member.photo) {
    return (
      <Photo
        image={member.photo}
        path={path && `${path}.photo`}
        ratio={ratio}
        rounded={rounded}
        sizes={sizes}
        className={className}
      >
        {children}
      </Photo>
    );
  }

  const radius = {
    none: "",
    lg: "rounded-lg",
    xl: "rounded-xl",
    "2xl": "rounded-2xl",
    "3xl": "rounded-3xl",
    full: "rounded-full",
  }[rounded];

  return (
    <div
      style={{ aspectRatio: ratio }}
      className={`@container relative flex w-full items-center justify-center overflow-hidden bg-primary/10 ${radius} ${className}`}
    >
      <span
        aria-hidden
        className="text-[clamp(1rem,32cqw,3.5rem)] font-semibold tracking-tight text-primary"
      >
        {initialsOf(member.name)}
      </span>
      {children}
    </div>
  );
}

function Name({
  member,
  path,
  align = "left",
}: {
  member: TeamMember;
  path: string;
  align?: "left" | "center";
}) {
  return (
    <div
      className={`flex flex-col gap-0.5 ${
        align === "center" ? "items-center text-center" : ""
      }`}
    >
      <h3 {...at(`${path}.name`, member.name)} className="font-medium">
        {member.name}
      </h3>
      <p {...at(`${path}.role`, member.role)} className="text-sm text-primary">
        {member.role}
      </p>
    </div>
  );
}

function Bio({ member, path }: { member: TeamMember; path: string }) {
  if (!member.bio) return null;
  return (
    <p
      {...at(`${path}.bio`, member.bio)}
      className="text-pretty text-sm leading-relaxed text-muted-foreground"
    >
      {rich(member.bio)}
    </p>
  );
}

function TeamPhotoGrid({ heading, subhead, members }: TeamSection) {
  return (
    <SectionShell type="team">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div className={`mt-14 grid gap-8 ${gridCols(members.length)}`}>
          {members.map((member, i) => (
            <div
              key={i}
              {...el(`members.${i}`, `Member ${i + 1}`)}
              className="flex flex-col gap-4"
            >
              <Avatar
                member={member}
                path={`members.${i}`}
                ratio="4/5"
                rounded="2xl"
                sizes={CARD_SIZE}
              />
              <Name member={member} path={`members.${i}`} />
              <Bio member={member} path={`members.${i}`} />
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function TeamCircleAvatars({ heading, subhead, members }: TeamSection) {
  return (
    <SectionShell type="team" tone="muted">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div className={`mt-14 grid gap-10 ${gridCols(members.length)}`}>
          {members.map((member, i) => (
            <div
              key={i}
              {...el(`members.${i}`, `Member ${i + 1}`)}
              className="flex flex-col items-center gap-4"
            >
              <div className="w-36">
                <Avatar
                  member={member}
                  path={`members.${i}`}
                  ratio="1/1"
                  rounded="full"
                  sizes="144px"
                />
              </div>
              <Name member={member} path={`members.${i}`} align="center" />
              <Bio member={member} path={`members.${i}`} />
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function TeamCardsWithBio({ heading, subhead, members }: TeamSection) {
  return (
    <SectionShell type="team">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div className={`mt-14 grid gap-6 ${gridCols(members.length)}`}>
          {members.map((member, i) => (
            <Card
              key={i}
              {...el(`members.${i}`, `Member ${i + 1}`)}
              className="flex flex-col gap-4 p-6"
            >
              <div className="flex items-center gap-4">
                <div className="w-16 shrink-0">
                  <Avatar
                    member={member}
                    path={`members.${i}`}
                    ratio="1/1"
                    rounded="full"
                    sizes="64px"
                  />
                </div>
                <Name member={member} path={`members.${i}`} />
              </div>
              <Bio member={member} path={`members.${i}`} />
            </Card>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function TeamRowsAlternating({ heading, subhead, members }: TeamSection) {
  return (
    <SectionShell type="team">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} align="left" />
        <div className="mt-14 flex flex-col gap-14">
          {members.map((member, i) => (
            <div
              key={i}
              {...el(`members.${i}`, `Member ${i + 1}`)}
              className="grid items-center gap-8 sm:grid-cols-[minmax(0,18rem)_1fr] sm:gap-12"
            >
              <Avatar
                member={member}
                path={`members.${i}`}
                ratio="1/1"
                rounded="3xl"
                sizes={HALF}
                className={i % 2 === 1 ? "sm:order-2" : ""}
              />
              <div className="flex flex-col gap-3">
                <Name member={member} path={`members.${i}`} />
                <Bio member={member} path={`members.${i}`} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function TeamCompactRow({ heading, subhead, members }: TeamSection) {
  return (
    <SectionShell type="team">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead
          heading={heading}
          subhead={subhead}
          align="left"
          size="md"
        />
        <div className="mt-10 flex flex-wrap gap-x-10 gap-y-6">
          {members.map((member, i) => (
            <div
              key={i}
              {...el(`members.${i}`, `Member ${i + 1}`)}
              className="flex items-center gap-3"
            >
              <div className="w-12 shrink-0">
                <Avatar
                  member={member}
                  path={`members.${i}`}
                  ratio="1/1"
                  rounded="full"
                  sizes="48px"
                />
              </div>
              <Name member={member} path={`members.${i}`} />
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function TeamOverlayNames({ heading, subhead, members }: TeamSection) {
  return (
    <SectionShell type="team">
      <div className={`${WIDE} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div className={`mt-14 grid gap-5 ${gridCols(members.length)}`}>
          {members.map((member, i) => (
            <div key={i} className="flex flex-col gap-3">
              <Avatar
                member={member}
                path={`members.${i}`}
                ratio="3/4"
                rounded="2xl"
                sizes={CARD_SIZE}
              >
                {member.photo && (
                  <>
                    <Scrim strength="md" />
                    <div className="absolute inset-x-0 bottom-0 flex flex-col gap-0.5 p-5">
                      <h3
                        {...at(`members.${i}.name`, member.name)}
                        className="font-medium text-white"
                      >
                        {member.name}
                      </h3>
                      <p
                        {...at(`members.${i}.role`, member.role)}
                        className="text-sm text-white/80"
                      >
                        {member.role}
                      </p>
                    </div>
                  </>
                )}
              </Avatar>
              {!member.photo && <Name member={member} path={`members.${i}`} />}
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

export const TEAM_VARIANTS: Record<TeamVariant, ComponentType<TeamSection>> = {
  "photo-grid": TeamPhotoGrid,
  "circle-avatars": TeamCircleAvatars,
  "cards-with-bio": TeamCardsWithBio,
  "rows-alternating": TeamRowsAlternating,
  "compact-row": TeamCompactRow,
  "overlay-names": TeamOverlayNames,
};

export const Team = TeamPhotoGrid;
