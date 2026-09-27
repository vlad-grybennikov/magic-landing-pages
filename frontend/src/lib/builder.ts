import type { Section, Theme } from "@/types/sections";
import type {
  Clarification,
  CommandResponse,
  PublishedRef,
  Readiness,
  ValidatedPage,
  VersionEntry,
  VersionSnapshot,
} from "@/lib/orchestrator";
import type { BuildDetail } from "@/lib/builds";

export interface Brief {
  business: string;
  audience: string;
  goal: string;
  tone?: string | null;
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  text: string;
  tone?: "error";
  clarification?: Clarification;
}

export type Phase =
  | "idle"
  | "running"
  | "saving"
  | "publishing"
  | "restoring"
  | "renaming";

export interface Rejection {
  stage: string;
  message: string;
}

export interface Conflict {
  expected: number;
  current: number;
}

export interface Draft {
  sections: Section[];
  theme: Theme | null;
  brief: Brief | null;
}

export interface EditorState {
  epoch: number;
  buildId: string | null;
  phase: Phase;
  page: ValidatedPage | null;
  versions: VersionEntry[];
  brief: Brief | null;
  summary: string;
  draft: Draft;
  messages: ChatMessage[];
  nextMessageId: number;
  sessionId: string | null;
  commandId: string | null;
  rejection: Rejection | null;
  conflict: Conflict | null;
  preview: VersionSnapshot | null;
  selectedIndex: number;
  selectedPath?: string;
}

export type EditorAction =
  | { type: "switch-build"; epoch: number; buildId: string | null }
  | {
      type: "reopened";
      epoch: number;
      build: BuildDetail;
      page: ValidatedPage | null;
      versions: VersionEntry[];
    }
  | { type: "begin"; epoch: number; phase: Exclude<Phase, "idle"> }
  | { type: "end"; epoch: number }
  | { type: "say"; message: Omit<ChatMessage, "id"> }
  | { type: "confirmed"; epoch: number; response: CommandResponse }
  | { type: "published"; epoch: number; published: PublishedRef }
  | { type: "renamed"; epoch: number; url: string }
  | {
      type: "restored";
      epoch: number;
      page: ValidatedPage;
      versions: VersionEntry[];
    }
  | { type: "rejected"; epoch: number; rejection: Rejection | null }
  | { type: "conflict"; epoch: number; conflict: Conflict | null }
  | { type: "command"; epoch: number; commandId: string | null }
  | { type: "session"; epoch: number; sessionId: string | null }
  | { type: "brief-saved"; epoch: number; brief: Brief | null }
  | {
      type: "refreshed";
      epoch: number;
      page: ValidatedPage;
      versions: VersionEntry[];
    }
  | { type: "edit-sections"; sections: Section[] }
  | { type: "edit-theme"; theme: Theme | null }
  | { type: "edit-brief"; brief: Brief | null }
  | { type: "undo" }
  | { type: "preview"; snapshot: VersionSnapshot | null }
  | { type: "select"; index: number; path?: string };

export const EMPTY_DRAFT: Draft = { sections: [], theme: null, brief: null };

export const INITIAL_STATE: EditorState = {
  epoch: 0,
  buildId: null,
  phase: "idle",
  page: null,
  versions: [],
  brief: null,
  summary: "",
  draft: EMPTY_DRAFT,
  messages: [],
  nextMessageId: 0,
  sessionId: null,
  commandId: null,
  rejection: null,
  conflict: null,
  preview: null,
  selectedIndex: 0,
  selectedPath: undefined,
};

export function asBrief(
  brief: CommandResponse["brief"] | BuildDetail["brief"] | null | undefined,
  fallbackBusiness = "",
): Brief | null {
  if (!brief && !fallbackBusiness) return null;
  return {
    business: brief?.business ?? fallbackBusiness,
    audience: brief?.audience ?? "--",
    goal: brief?.goal ?? "--",
    tone: brief?.tone ?? null,
  };
}

function draftFrom(page: ValidatedPage | null, brief: Brief | null): Draft {
  return {
    sections: page?.sections ?? [],
    theme: page?.theme ?? null,
    brief,
  };
}

function stale(state: EditorState, epoch: number): boolean {
  return epoch !== state.epoch;
}

function keepSelection(
  state: EditorState,
  next: Section[],
  samePage: boolean,
): Pick<EditorState, "selectedIndex" | "selectedPath"> {
  if (!samePage) return { selectedIndex: 0, selectedPath: undefined };
  const current = state.draft.sections[state.selectedIndex]?.type;
  const kept = current ? next.findIndex((s) => s.type === current) : -1;
  return {
    selectedIndex: kept < 0 && state.selectedIndex >= 0 ? 0 : kept,
    selectedPath: kept >= 0 ? state.selectedPath : undefined,
  };
}

export function reduce(state: EditorState, action: EditorAction): EditorState {
  switch (action.type) {
    case "switch-build":
      if (action.epoch <= state.epoch) return state;
      return {
        ...INITIAL_STATE,
        epoch: action.epoch,
        buildId: action.buildId,
      };

    case "reopened": {
      if (stale(state, action.epoch)) return state;
      const brief = asBrief(action.build.brief, action.page?.name ?? "");
      return {
        ...state,
        buildId: action.build.id,
        page: action.page,
        versions: action.versions,
        brief,
        summary:
          action.build.summary ??
          (action.page ? `Editing ${action.page.name}.` : ""),
        draft: draftFrom(action.page, brief),
        messages: action.build.messages.map((message, i) => ({
          ...(message as Omit<ChatMessage, "id">),
          id: i,
        })),
        nextMessageId: action.build.messages.length,
      };
    }

    case "begin":
      if (stale(state, action.epoch)) return state;
      return {
        ...state,
        phase: action.phase,
        rejection: null,
        conflict: null,
        preview: null,
      };

    case "end":
      if (stale(state, action.epoch)) return state;
      return { ...state, phase: "idle" };

    case "say":
      return {
        ...state,
        messages: [...state.messages, { id: state.nextMessageId, ...action.message }],
        nextMessageId: state.nextMessageId + 1,
      };

    case "confirmed": {
      if (stale(state, action.epoch)) return state;
      const { response } = action;
      const sessionId =
        response.clarification?.sessionId ?? response.sessionId ?? state.sessionId;
      if (!response.page) {
        return { ...state, sessionId, summary: response.summary || state.summary };
      }
      const samePage = response.page.id === state.page?.id;
      const name = response.page.name ?? "";
      const renamed = samePage && !!name && name !== state.page?.name;
      const brief = samePage
        ? renamed && state.brief
          ? { ...state.brief, business: name }
          : state.brief
        : asBrief(response.brief, name);
      const draftBrief = samePage
        ? renamed && state.draft.brief
          ? { ...state.draft.brief, business: name }
          : state.draft.brief
        : brief;
      return {
        ...state,
        sessionId,
        page: response.page,
        versions: response.versions ?? state.versions,
        brief,
        summary: response.summary || state.summary,
        draft: { ...draftFrom(response.page, brief), brief: draftBrief },
        conflict: null,
        ...keepSelection(state, response.page.sections, samePage),
      };
    }

    case "published":
      if (stale(state, action.epoch) || !state.page) return state;
      return {
        ...state,
        page: { ...state.page, published: action.published },
        versions: state.versions.map((v) => ({
          ...v,
          published: v.version === action.published.version,
        })),
      };

    case "renamed":
      if (stale(state, action.epoch) || !state.page) return state;
      return { ...state, page: { ...state.page, url: action.url } };

    case "restored":
      if (stale(state, action.epoch)) return state;
      return {
        ...state,
        page: action.page,
        versions: action.versions,
        draft: draftFrom(action.page, state.draft.brief),
        preview: null,
        selectedIndex: 0,
        selectedPath: undefined,
      };

    case "rejected":
      if (stale(state, action.epoch)) return state;
      return { ...state, rejection: action.rejection };

    case "conflict":
      if (stale(state, action.epoch)) return state;
      return { ...state, conflict: action.conflict };

    case "command":
      if (stale(state, action.epoch)) return state;
      return { ...state, commandId: action.commandId };

    case "session":
      if (stale(state, action.epoch)) return state;
      return { ...state, sessionId: action.sessionId };

    case "edit-sections":
      return { ...state, draft: { ...state.draft, sections: action.sections } };

    case "edit-theme":
      return { ...state, draft: { ...state.draft, theme: action.theme } };

    case "edit-brief":
      return { ...state, draft: { ...state.draft, brief: action.brief } };

    case "undo":
      return { ...state, draft: draftFrom(state.page, state.brief) };

    case "brief-saved":
      if (stale(state, action.epoch)) return state;
      return { ...state, brief: action.brief };

    case "refreshed":
      if (stale(state, action.epoch)) return state;
      return {
        ...state,
        page: action.page,
        versions: action.versions,
        conflict: null,
      };

    case "preview":
      return {
        ...state,
        preview: action.snapshot,
        selectedIndex: 0,
        selectedPath: undefined,
      };

    case "select":
      return { ...state, selectedIndex: action.index, selectedPath: action.path };
  }
}

export function isPublished(page: ValidatedPage | null): boolean {
  return !!page && page.published?.version === page.version;
}

export function hasLiveCopy(page: ValidatedPage | null): boolean {
  return !!page?.published;
}

export function readinessOf(page: ValidatedPage | null): Readiness | null {
  return page?.readiness ?? null;
}

export type PublishHold = "placeholder" | "review";

export function publishHold(readiness: Readiness | null): PublishHold | null {
  if (!readiness) return null;
  if (readiness.blocking.length > 0) return "placeholder";
  return readiness.warnings.length > 0 ? "review" : null;
}

export function recolouredKeys(
  draft: Theme | null,
  saved: Theme | null | undefined,
): Array<"primary" | "accent" | "background"> {
  return (["primary", "accent", "background"] as const).filter(
    (key) => !!draft && !!saved && draft[key] !== saved[key],
  );
}

export function briefChanges(
  draft: Brief | null,
  saved: Brief | null,
): { renamed: boolean; rebriefed: boolean } {
  if (!draft || !saved) return { renamed: false, rebriefed: false };
  return {
    renamed: draft.business.trim() !== saved.business,
    rebriefed: draft.audience !== saved.audience || draft.goal !== saved.goal,
  };
}

export function isBusy(phase: Phase): boolean {
  return phase !== "idle";
}
