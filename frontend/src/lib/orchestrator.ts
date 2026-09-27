import type { components } from "@/generated/api";
import type { Section, Theme } from "@/types/sections";
import { authedFetch } from "@/lib/api";

export type Schemas = components["schemas"];

export type Readiness = Schemas["Readiness"];
export type ReadinessIssue = Schemas["ReadinessIssue"];
export type PublishedRef = Schemas["PublishedRef"];
export type VersionEntry = Schemas["VersionEntry"];
export type Clarification = Schemas["Clarification"];
export type ClarificationField = Schemas["ClarificationField"];
export type Plan = Schemas["Plan"];
export type ValidationStatus = Schemas["ValidationStatus"];
export type ErrorDetail = Schemas["ErrorDetail"];
export type Brief = Schemas["Brief"];
export type StepEvent = Schemas["StepEvent"];
export type StreamEvent = Schemas["StreamEvent"];
export type CommandRecord = Schemas["CommandRecord"];
export type PublishResponse = Schemas["PublishResponse"];
export type RenameResponse = Schemas["RenameResponse"];
export type ImageCandidate = Schemas["ImageCandidate"];
export type ModelInfo = Schemas["ModelInfo"];

export interface ValidatedPage
  extends Omit<Schemas["PageView"], "sections" | "theme"> {
  sections: Section[];
  theme?: Theme | null;
}

export interface CommandResponse
  extends Omit<Schemas["CommandResponse"], "page"> {
  page?: ValidatedPage | null;
}

export interface VersionSnapshot
  extends Omit<Schemas["VersionSnapshot"], "sections" | "theme"> {
  sections: Section[];
  theme?: Theme | null;
}

export interface RestoreResult
  extends Omit<Schemas["RestoreResponse"], "page"> {
  page: ValidatedPage;
}

export class CommandRejected extends Error {
  constructor(
    public recognizedCommand: string,
    public stage: string,
    message: string,
    public detail: ErrorDetail | null = null,
    public commandId: string | null = null,
  ) {
    super(message);
    this.name = "CommandRejected";
  }

  get conflict(): { expected: number; current: number } | null {
    if (this.stage !== "conflict" || this.detail?.current == null) return null;
    return {
      expected: this.detail.expected ?? 0,
      current: this.detail.current,
    };
  }
}

async function rejection(
  res: Response,
  recognizedCommand = "",
  fallbackStage = "edit",
): Promise<CommandRejected> {
  const data = (await res.json().catch(() => null)) as {
    error?: ErrorDetail;
    commandId?: string;
  } | null;
  return new CommandRejected(
    recognizedCommand,
    data?.error?.stage ?? fallbackStage,
    data?.error?.message ?? `Orchestrator returned ${res.status}`,
    data?.error ?? null,
    data?.commandId ?? null,
  );
}

async function json<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await authedFetch(path, {
    ...init,
    headers: {
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) throw await rejection(res);
  return res.json() as Promise<T>;
}

export interface CommandContext {
  sessionId?: string | null;
  pageId?: string | null;
  buildId?: string | null;
  answering?: boolean;
  section?: string | null;
  model?: string | null;
  idempotencyKey?: string | null;
}

export type CommandStep = Omit<StepEvent, "type" | "commandId"> & {
  commandId?: string;
};

export function newIdempotencyKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

async function* frames(res: Response): AsyncGenerator<StreamEvent> {
  if (!res.body) return;
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const line = chunk.split("\n").find((l) => l.startsWith("data:"));
      if (line) yield JSON.parse(line.slice(5)) as StreamEvent;
    }
  }
}

async function consume(
  res: Response,
  transcript: string,
  onStep: (step: CommandStep) => void,
  onCommand?: (commandId: string) => void,
): Promise<CommandResponse> {
  let spoken = transcript;
  for await (const event of frames(res)) {
    switch (event.type) {
      case "command":
        onCommand?.(event.commandId);
        break;
      case "step":
        if (event.tool === "transcribed") spoken = event.text ?? spoken;
        onStep(event);
        break;
      case "error":
        throw new CommandRejected(
          spoken,
          event.error.stage,
          event.error.message,
          event.error,
          event.commandId,
        );
      case "result":
        return event.result as CommandResponse;
      case "status":
        throw new DetachedCommand(event.commandId, event.status);
    }
  }
  throw new Error("The orchestrator closed the connection early.");
}

export class DetachedCommand extends Error {
  constructor(
    public commandId: string,
    public status: string,
  ) {
    super(`Command ${commandId} is ${status} on another worker.`);
    this.name = "DetachedCommand";
  }
}

export async function streamCommand(
  input: { text: string } | { audio: Blob },
  ctx: CommandContext,
  onStep: (step: CommandStep) => void,
  onCommand?: (commandId: string) => void,
): Promise<CommandResponse> {
  const spoken = "audio" in input;
  const key = ctx.idempotencyKey ?? newIdempotencyKey();
  let request: RequestInit;

  if (spoken) {
    const form = new FormData();
    form.append("file", input.audio, "command.webm");
    if (ctx.sessionId) form.append("session_id", ctx.sessionId);
    if (ctx.pageId) form.append("page_id", ctx.pageId);
    if (ctx.buildId) form.append("build_id", ctx.buildId);
    if (ctx.section) form.append("section", ctx.section);
    if (ctx.model) form.append("model", ctx.model);
    if (ctx.answering) form.append("answering", "true");
    form.append("idempotency_key", key);
    request = { method: "POST", body: form };
  } else {
    request = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: input.text,
        session_id: ctx.sessionId ?? null,
        page_id: ctx.pageId ?? null,
        build_id: ctx.buildId ?? null,
        section: ctx.section ?? null,
        model: ctx.model ?? null,
        answering: ctx.answering ?? false,
        idempotency_key: key,
      }),
    };
  }

  const res = await authedFetch(
    spoken ? "/command/stream" : "/command/text/stream",
    request,
  );
  if (!res.ok || !res.body) {
    throw new Error(`Orchestrator returned ${res.status} ${res.statusText}`);
  }
  return consume(res, spoken ? "" : input.text, onStep, onCommand);
}

export async function reattachCommand(
  commandId: string,
  onStep: (step: CommandStep) => void,
): Promise<CommandResponse> {
  const res = await authedFetch(`/commands/${commandId}/events`);
  if (!res.ok || !res.body) {
    throw new Error(`Orchestrator returned ${res.status} ${res.statusText}`);
  }
  return consume(res, "", onStep);
}

export function fetchCommand(commandId: string): Promise<CommandRecord> {
  return json<CommandRecord>(`/commands/${commandId}`);
}

export function cancelCommand(commandId: string): Promise<CommandRecord> {
  return json<CommandRecord>(`/commands/${commandId}`, { method: "DELETE" });
}

export type EditAction =
  | "editContent"
  | "replaceImage"
  | "addSection"
  | "removeSection"
  | "moveSection"
  | "setVariant"
  | "addItem"
  | "removeItem"
  | "moveItem"
  | "setIcon"
  | "setTheme"
  | "setName"
  | "approveSection"
  | "regenerateSection";

export interface EditChange {
  action: EditAction;
  args: Record<string, string>;
}

export async function applyEdits(
  pageId: string,
  expectedVersion: number,
  changes: EditChange[],
): Promise<CommandResponse> {
  return json<CommandResponse>("/edit", {
    method: "POST",
    body: JSON.stringify({
      page_id: pageId,
      expected_version: expectedVersion,
      changes,
    }),
  });
}

export function publishPage(
  pageId: string,
  version?: number,
): Promise<PublishResponse> {
  return json<PublishResponse>("/publish", {
    method: "POST",
    body: JSON.stringify({ page_id: pageId, version: version ?? null }),
  });
}

export function unpublishPage(pageId: string): Promise<{ published: boolean }> {
  return json("/unpublish", {
    method: "POST",
    body: JSON.stringify({ page_id: pageId }),
  });
}

export function renamePage(
  pageId: string,
  wanted: string,
): Promise<RenameResponse> {
  return json<RenameResponse>("/pages/url", {
    method: "POST",
    body: JSON.stringify({ page_id: pageId, wanted }),
  });
}

export function fetchVersion(
  pageId: string,
  version: number,
): Promise<VersionSnapshot> {
  return json<VersionSnapshot>(
    `/versions/${version}?page_id=${encodeURIComponent(pageId)}`,
  );
}

export function restoreVersion(
  pageId: string,
  version: number,
  expectedVersion?: number,
): Promise<RestoreResult> {
  return json<RestoreResult>("/versions/restore", {
    method: "POST",
    body: JSON.stringify({
      page_id: pageId,
      version,
      expected_version: expectedVersion ?? null,
    }),
  });
}

export async function fetchModels(): Promise<ModelInfo[]> {
  const res = await authedFetch("/models");
  if (!res.ok) return [];
  const data = (await res.json()) as { models?: ModelInfo[] };
  return data.models ?? [];
}

export async function searchImages(query: string): Promise<ImageCandidate[]> {
  if (!query.trim()) return [];
  const res = await authedFetch(`/images?q=${encodeURIComponent(query)}`);
  if (!res.ok) return [];
  const data = (await res.json()) as { images?: ImageCandidate[] };
  return data.images ?? [];
}

export async function searchIcons(
  query: string,
  k = 80,
): Promise<ImageCandidate[]> {
  const res = await authedFetch(
    `/icons?q=${encodeURIComponent(query.trim())}&k=${k}`,
  );
  if (!res.ok) return [];
  const data = (await res.json()) as { icons?: ImageCandidate[] };
  return data.icons ?? [];
}
