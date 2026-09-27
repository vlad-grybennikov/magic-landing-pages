"use client";

import { useEffect, useRef, useState } from "react";
import type { Clarification, ModelInfo } from "@/lib/orchestrator";
import type { Progress } from "@/lib/steps";
import type { SectionType } from "@/types/sections";
import { SECTION_LABELS } from "@/data/build-mock";
import { MicIcon, SendIcon, SparklesIcon } from "./icons";
import { ModelMenu } from "./ModelMenu";

import type { ChatMessage } from "@/lib/builder";
export type { ChatMessage };

export function Chat({
  messages,
  isRecording,
  isWorking,
  isPublishing,
  hasPage,
  compact = false,
  progress,
  selectedSection,
  models,
  model,
  onClearSection,
  onModelChange,
  onSend,
  onMicClick,
}: {
  messages: ChatMessage[];
  isRecording: boolean;
  isWorking: boolean;
  isPublishing: boolean;
  hasPage: boolean;
  compact?: boolean;
  progress: Progress | null;
  selectedSection: SectionType | null;
  models: ModelInfo[];
  model: string | null;
  onClearSection: () => void;
  onModelChange: (model: string | null) => void;
  onSend: (text: string) => void;
  onMicClick: () => void;
}) {
  const [draft, setDraft] = useState("");
  const busy = isWorking || isPublishing;

  const send = () => {
    if (!draft.trim() || busy) return;
    onSend(draft.trim());
    setDraft("");
  };

  const hasHistory =
    messages.length > 0 || isRecording || isWorking || isPublishing;
  const last = messages[messages.length - 1];
  const pending = !isWorking ? last?.clarification : undefined;
  const hasChoices = pending?.fields?.some((f) => f.options.length) ?? false;

  return (
    <header
      className={`panel flex h-full min-h-0 w-full flex-col sm:h-auto ${
        compact ? "sm:max-h-[19rem]" : "sm:max-h-[22rem]"
      }`}
    >
      <Transcript
        messages={messages}
        isRecording={isRecording}
        isWorking={isWorking}
        isPublishing={isPublishing}
        progress={progress}
        onAnswer={onSend}
      />
      <div
        className={`shrink-0 p-3 ${hasHistory ? "border-t border-ui-border" : ""}`}
      >
        <div
          className={`rounded-xl border bg-ui-surface transition-colors ${
            isRecording
              ? "border-red-300 ring-2 ring-red-100"
              : "border-ui-border focus-within:border-ui-accent focus-within:ring-2 focus-within:ring-ui-accent/15"
          }`}
        >
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            disabled={busy}
            rows={1}
            aria-label="Ask for a page, or answer the question"
            placeholder={
              isRecording
                ? "Listening… tap the mic again to send"
                : pending
                  ? hasChoices
                    ? "Type your answer, or pick one below"
                    : "Type your answer"
                  : hasPage
                    ? "Ask for a change -- “make the hero headline shorter”"
                    : "Describe the landing page you want"
            }
            className="block max-h-40 w-full resize-none bg-transparent px-3.5 pb-1 pt-2.5 text-sm leading-6 text-ui-text outline-none placeholder:text-ui-faint disabled:opacity-50"
          />

          <div className="flex items-center gap-2 px-2 pb-2">
            <ModelMenu
              models={models}
              value={model}
              onChange={onModelChange}
              disabled={busy}
            />

            {selectedSection && (
              <span className="flex items-center gap-1 rounded-md bg-ui-accent-soft py-1 pl-2 pr-1 text-xs font-medium text-ui-accent">
                @{SECTION_LABELS[selectedSection]}
                <button
                  type="button"
                  onClick={onClearSection}
                  aria-label="Stop scoping to this section"
                  className="rounded px-1 leading-none hover:bg-ui-accent/10"
                >
                  ×
                </button>
              </span>
            )}

            <span className="ml-auto flex items-center gap-1">
              <button
                type="button"
                onClick={onMicClick}
                disabled={busy}
                aria-pressed={isRecording}
                aria-label={isRecording ? "Stop recording" : "Start recording"}
                className={`flex h-8 w-8 items-center justify-center rounded-lg transition-colors disabled:opacity-40 ${
                  isRecording
                    ? "bg-red-500 text-white"
                    : "text-ui-muted hover:bg-ui-inset hover:text-ui-text"
                }`}
              >
                <MicIcon className="h-4 w-4" />
              </button>

              <button
                type="button"
                onClick={send}
                disabled={busy || !draft.trim()}
                aria-label="Send"
                className="brand-gradient flex h-8 w-8 items-center justify-center rounded-lg text-white transition-all hover:brightness-110 disabled:bg-none disabled:bg-ui-border-strong"
              >
                <SendIcon className="h-4 w-4" />
              </button>
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}

function Transcript({
  messages,
  isRecording,
  isWorking,
  isPublishing,
  progress,
  onAnswer,
}: {
  messages: ChatMessage[];
  isRecording: boolean;
  isWorking: boolean;
  isPublishing: boolean;
  progress: Progress | null;
  onAnswer: (text: string) => void;
}) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "nearest" });
  }, [messages.length, isWorking]);

  if (messages.length === 0 && !isRecording && !isWorking && !isPublishing) {
    return null;
  }

  return (
    <div className="min-h-0 flex-1 overflow-y-auto rounded-t-[13px] bg-ui-surface px-4 py-3.5">
      {
        <div className="flex flex-col gap-3.5">
          {messages.map((message, i) => (
            <Bubble
              key={message.id}
              message={message}
              answerable={i === messages.length - 1 && !isWorking}
              onAnswer={onAnswer}
            />
          ))}

          {isWorking && progress ? (
            <ProgressLine progress={progress} />
          ) : (
            (isRecording || isWorking || isPublishing) && (
              <Status
                label={
                  isRecording
                    ? "Listening…"
                    : isPublishing
                      ? "Publishing your page…"
                      : "Working on it…"
                }
                recording={isRecording}
              />
            )
          )}
        </div>
      }
      <div ref={endRef} />
    </div>
  );
}

function Bubble({
  message,
  answerable,
  onAnswer,
}: {
  message: ChatMessage;
  answerable: boolean;
  onAnswer: (text: string) => void;
}) {
  if (message.role === "user") {
    return (
      <p className="animate-message ml-auto max-w-[85%] rounded-2xl rounded-br-lg bg-ui-inset px-3.5 py-2 text-sm leading-6 text-ui-text sm:max-w-[34rem]">
        {message.text}
      </p>
    );
  }

  return (
    <div className="animate-message flex max-w-full gap-2.5">
      <span
        className={`mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${
          message.tone === "error"
            ? "bg-ui-danger-soft text-ui-danger"
            : "brand-gradient text-white"
        }`}
        aria-hidden
      >
        {message.tone === "error" ? (
          <span className="text-[10px] font-semibold">!</span>
        ) : (
          <SparklesIcon className="h-2.5 w-2.5" />
        )}
      </span>

      <div className="min-w-0 flex-1">
        <p
          className={`text-sm leading-6 ${
            message.tone === "error" ? "text-ui-danger" : "text-ui-text"
          }`}
        >
          {message.text}
        </p>
        {message.clarification && answerable && (
          <Choices clarification={message.clarification} onAnswer={onAnswer} />
        )}
      </div>
    </div>
  );
}

function Choices({
  clarification,
  onAnswer,
}: {
  clarification: Clarification;
  onAnswer: (text: string) => void;
}) {
  const [picks, setPicks] = useState<Record<string, string>>({});
  const [typed, setTyped] = useState<Record<string, boolean>>({});
  const fields = clarification.fields ?? [];

  if (!fields.some((f) => f.options.length)) return null;

  const send = (values: Record<string, string>) => {
    if (!fields.every((f) => values[f.name]?.trim())) return;
    onAnswer(fields.map((f) => values[f.name].trim()).join(", "));
  };

  const choose = (name: string, value: string) => {
    const next = { ...picks, [name]: value };
    setPicks(next);
    setTyped((prev) => ({ ...prev, [name]: false }));
    send(next);
  };

  const type = (name: string, value: string) =>
    setPicks((prev) => ({ ...prev, [name]: value }));

  return (
    <div className="mt-2 flex flex-col gap-3">
      {fields.map((field) => {
        const writing = typed[field.name] || !field.options.length;
        return (
          <div key={field.name}>
            {fields.length > 1 && (
              <p className="mb-1.5 text-[11px] font-medium uppercase tracking-[0.06em] text-ui-faint">
                {field.question}
              </p>
            )}

            {!!field.options.length && (
              <div className="flex flex-wrap gap-1.5">
                {field.options.map((option) => (
                  <Chip
                    key={option}
                    label={option}
                    active={!writing && picks[field.name] === option}
                    onClick={() => choose(field.name, option)}
                  />
                ))}
                <Chip
                  label="Something else…"
                  active={writing}
                  onClick={() => {
                    setTyped((prev) => ({ ...prev, [field.name]: true }));
                    type(field.name, "");
                  }}
                />
              </div>
            )}

            {writing && (
              <input
                autoFocus={typed[field.name]}
                value={picks[field.name] ?? ""}
                onChange={(e) => type(field.name, e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send(picks)}
                placeholder={field.question}
                aria-label={field.question}
                className="mt-1.5 w-full rounded-lg border border-ui-border bg-ui-surface px-3 py-1.5 text-sm text-ui-text outline-none placeholder:text-ui-faint focus:border-ui-accent focus:ring-2 focus:ring-ui-accent/15"
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

function Chip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-lg border px-3 py-1.5 text-sm transition-colors ${
        active
          ? "border-ui-accent bg-ui-accent text-white"
          : "border-ui-border bg-ui-surface text-ui-text hover:border-ui-accent/40 hover:bg-ui-accent-soft"
      }`}
    >
      {label}
    </button>
  );
}

function ProgressLine({ progress }: { progress: Progress }) {
  const share = progress.total
    ? Math.min(100, Math.round((progress.done / progress.total) * 100))
    : 0;

  return (
    <div className="animate-message ml-[1.875rem] flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-3">
        <span className="truncate text-sm text-ui-muted">
          {progress.label}…
        </span>
        {progress.total > 0 && (
          <span className="shrink-0 text-xs tabular-nums text-ui-faint">
            {progress.done}/{progress.total}
          </span>
        )}
      </div>
      <span className="h-1 w-full overflow-hidden rounded-full bg-ui-border">
        <span
          className="brand-gradient block h-full rounded-full transition-[width] duration-300"
          style={{ width: `${share}%` }}
        />
      </span>
    </div>
  );
}

function Status({ label, recording }: { label: string; recording: boolean }) {
  return (
    <p className="animate-message ml-[1.875rem] flex items-center gap-2 text-sm text-ui-muted">
      <span
        className={`h-2 w-2 animate-pulse rounded-full ${
          recording ? "bg-red-500" : "bg-ui-accent"
        }`}
      />
      {label}
    </p>
  );
}
