"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import type { Theme } from "@/types/sections";
import {
  CommandRejected,
  DetachedCommand,
  applyEdits,
  fetchCommand,
  fetchModels,
  newIdempotencyKey,
  publishPage,
  renamePage,
  fetchVersion,
  restoreVersion,
  streamCommand,
  type CommandResponse,
  type CommandStep,
  type EditChange,
  type ModelInfo,
} from "@/lib/orchestrator";
import { advance, type Progress } from "@/lib/steps";
import { useAuth } from "@/lib/auth";
import {
  attachPage,
  createBuild,
  listBuilds,
  openBuild,
  saveBuild,
  type BuildSummary,
} from "@/lib/builds";
import {
  INITIAL_STATE,
  briefChanges,
  hasLiveCopy,
  isBusy,
  isPublished,
  publishHold,
  recolouredKeys,
  reduce,
  type ChatMessage,
  type Phase,
} from "@/lib/builder";
import { LoginScreen } from "@/components/build/LoginScreen";
import { useRecorder } from "@/components/build/useRecorder";
import { Chat } from "@/components/build/Chat";
import {
  changedFields,
  editByRole,
  fieldForRole,
} from "@/components/build/EditPanel";
import { TopBar } from "@/components/build/TopBar";
import { PageCanvas } from "@/components/build/PageCanvas";
import { Inspector } from "@/components/build/Inspector";
import { MediaPicker } from "@/components/build/MediaPicker";
import { SECTION_LABELS } from "@/lib/sections";
import { PageConfig } from "@/components/build/PageConfig";
import { EmptyState } from "@/components/build/EmptyState";
import { ConflictBar } from "@/components/build/ConflictBar";
import { describe, issueFor } from "@/components/build/ReviewMenu";
import { ViewTabs, type BuilderView } from "@/components/build/ViewTabs";

const RECOVERY_POLL_MS = 1500;

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export default function BuilderPage() {
  const { user, isLoading, required, logout } = useAuth();
  const recorder = useRecorder();
  const [state, dispatch] = useReducer(reduce, INITIAL_STATE);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [picking, setPicking] = useState<{
    path: string;
    kind: "image" | "icon";
  } | null>(null);
  const [reveal, setReveal] = useState(0);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [model, setModel] = useState<string | null>(null);
  const [builds, setBuilds] = useState<BuildSummary[]>([]);
  const [view, setView] = useState<BuilderView>("canvas");
  const [panelsOpen, setPanelsOpen] = useState(false);

  const latest = useRef(state);
  latest.current = state;
  const epochs = useRef(0);

  const switchBuild = useCallback((id: string | null) => {
    const next = ++epochs.current;
    dispatch({ type: "switch-build", epoch: next, buildId: id });
    setView("canvas");
    setPanelsOpen(false);
    return next;
  }, []);

  const {
    buildId,
    phase,
    page,
    versions,
    brief: savedBrief,
    summary,
    draft,
    messages,
    sessionId,
    rejection,
    conflict,
    preview,
    selectedIndex,
    selectedPath,
  } = state;

  const busy = isBusy(phase);
  const isWorking = busy && phase !== "publishing";
  const isPublishing = phase === "publishing";
  const published = isPublished(page);
  const live = hasLiveCopy(page);
  const answering = messages[messages.length - 1]?.clarification != null;
  const sections = draft.sections;
  const selected = (preview?.sections ?? sections)[selectedIndex];
  const selectedType = selected?.type ?? null;

  const say = useCallback(
    (message: Omit<ChatMessage, "id">) => dispatch({ type: "say", message }),
    [],
  );

  const begin = useCallback((next: Exclude<Phase, "idle">) => {
    const at = epochs.current;
    dispatch({ type: "begin", epoch: at, phase: next });
    return at;
  }, []);

  const end = useCallback((at: number) => dispatch({ type: "end", epoch: at }), []);

  const refreshBuilds = useCallback(async () => {
    try {
      setBuilds(await listBuilds());
    } catch {
    }
  }, []);

  const startBuild = useCallback(async () => {
    const at = switchBuild(null);
    try {
      const build = await createBuild();
      dispatch({
        type: "reopened",
        epoch: at,
        build: { ...build, messages: [], brief: null, summary: null },
        page: null,
        versions: [],
      });
      await refreshBuilds();
    } catch {
    }
  }, [refreshBuilds, switchBuild]);

  const reopenBuild = useCallback(async (id: string) => {
    const at = switchBuild(id);
    try {
      const opened = await openBuild(id);
      dispatch({ type: "reopened", epoch: at, ...opened });
    } catch {
    }
  }, [switchBuild]);

  const refreshPage = useCallback(async () => {
    const { buildId: current } = latest.current;
    const at = epochs.current;
    if (!current) return;
    try {
      const opened = await openBuild(current);
      if (opened.page) {
        dispatch({
          type: "refreshed",
          epoch: at,
          page: opened.page,
          versions: opened.versions,
        });
      }
    } catch {
    }
  }, []);

  useEffect(() => {
    if (!panelsOpen) return;
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setPanelsOpen(false);
    };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [panelsOpen]);

  useEffect(() => {
    if (isLoading || !user) return;
    let cancelled = false;
    fetchModels()
      .then((available) => {
        if (!cancelled) setModels(available);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [isLoading, user]);

  useEffect(() => {
    if (isLoading || !user || buildId) return;
    let cancelled = false;

    (async () => {
      try {
        const saved = await listBuilds();
        if (cancelled) return;
        setBuilds(saved);
        const resumable = saved.find((b) => !b.pageId && b.turns === 0);
        if (resumable) await reopenBuild(resumable.id);
        else await startBuild();
      } catch {
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isLoading, user, buildId, startBuild, reopenBuild]);

  const absorb = useCallback(
    async (at: number, response: CommandResponse) => {
      const previous = latest.current.page?.id ?? null;
      dispatch({ type: "confirmed", epoch: at, response });
      say({
        role: "assistant",
        text: response.message,
        clarification: response.clarification ?? undefined,
      });
      const build = latest.current.buildId;
      if (response.page && response.page.id !== previous && build) {
        try {
          await attachPage(build, response.page.id);
        } catch {
        }
      }
    },
    [say],
  );

  const reportFailure = useCallback(
    (at: number, e: unknown, echoSpoken = false) => {
      if (e instanceof CommandRejected) {
        dispatch({
          type: "rejected",
          epoch: at,
          rejection: { stage: e.stage, message: e.message },
        });
        if (e.conflict) dispatch({ type: "conflict", epoch: at, conflict: e.conflict });
        if (echoSpoken && e.recognizedCommand) {
          say({ role: "user", text: e.recognizedCommand });
        }
        const readiness = e.detail?.readiness;
        const reasons = [
          ...(readiness?.blocking ?? []),
          ...(readiness?.warnings ?? []),
        ].map(describe);
        say({
          role: "assistant",
          tone: "error",
          text: reasons.length
            ? `${e.message} ${reasons.join(", ")}.`
            : `Rejected at the ${e.stage} gate -- ${e.message}`,
        });
      } else {
        const text =
          e instanceof Error
            ? `Couldn't reach the orchestrator (${e.message}).`
            : "Something went wrong.";
        say({ role: "assistant", tone: "error", text });
      }
    },
    [say],
  );

  const recover = useCallback(
    async (at: number, commandId: string): Promise<CommandResponse> => {
      for (;;) {
        if (epochs.current !== at) throw new Error("build changed");
        const record = await fetchCommand(commandId);
        if (record.status === "done" && record.result) {
          return record.result as CommandResponse;
        }
        if (record.status === "failed" || record.status === "cancelled") {
          throw new CommandRejected(
            "",
            record.error?.stage ?? record.status,
            record.error?.message ?? record.status,
            record.error ?? null,
            commandId,
          );
        }
        await sleep(RECOVERY_POLL_MS);
      }
    },
    [],
  );

  const run = async (input: { text: string } | { audio: Blob }) => {
    const spoken = "audio" in input;
    if (!spoken) say({ role: "user", text: input.text });
    const at = begin("running");
    setProgress(null);
    const key = newIdempotencyKey();

    const onStep = (step: CommandStep) => {
      if (epochs.current !== at) return;
      if (step.tool === "transcribed" && step.text) {
        say({ role: "user", text: step.text });
      }
      setProgress((prev) => advance(prev, step));
    };
    const onCommand = (commandId: string) =>
      dispatch({ type: "command", epoch: at, commandId });
    const context = {
      sessionId,
      pageId: page?.id ?? null,
      buildId,
      answering,
      section: selectedType,
      model,
      idempotencyKey: key,
    };

    try {
      let response: CommandResponse;
      try {
        response = await streamCommand(input, context, onStep, onCommand);
      } catch (e) {
        if (e instanceof DetachedCommand) {
          response = await recover(at, e.commandId);
        } else if (
          e instanceof TypeError &&
          latest.current.commandId &&
          epochs.current === at
        ) {
          response = await recover(at, latest.current.commandId);
        } else {
          throw e;
        }
      }
      await absorb(at, response);
    } catch (e) {
      reportFailure(at, e, spoken);
    } finally {
      end(at);
      setProgress(null);
    }
  };

  const handleMicClick = async () => {
    if (busy) return;

    if (recorder.isRecording) {
      await run({ audio: await recorder.stop() });
      return;
    }

    try {
      await recorder.start();
    } catch {
      say({
        role: "assistant",
        tone: "error",
        text: "Microphone access was denied -- type your request instead.",
      });
    }
  };

  const runStructuralEdit = async (change: EditChange) => {
    if (!page) return;
    const at = begin("saving");
    try {
      await absorb(at, await applyEdits(page.id, page.version, [change]));
    } catch (e) {
      reportFailure(at, e);
    } finally {
      end(at);
    }
  };

  const editSectionField = useCallback(
    (
      index: number,
      target: { role?: string; path?: string },
      value: string,
    ) => {
      const section = sections[index];
      if (!section) return;
      const path =
        target.path ??
        (!value && target.role
          ? fieldForRole(section, target.role)
          : undefined);
      if (path) {
        void runStructuralEdit({
          action: "editContent",
          args: { section: section.type, path, value },
        });
        return;
      }
      if (!target.role) return;
      dispatch({
        type: "edit-sections",
        sections: sections.map((section, i) => {
          if (i !== index) return section;
          return editByRole(section, target.role as string, value) ?? section;
        }),
      });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [sections, page?.id, page?.version],
  );

  const handleSend = async (text: string) => {
    if (busy || !text.trim()) return;
    await run({ text: text.trim() });
  };

  const handlePreviewVersion = async (version?: number) => {
    if (!page || busy) return;
    if (version === undefined) {
      dispatch({ type: "preview", snapshot: null });
      return;
    }
    const at = epochs.current;
    try {
      const snapshot = await fetchVersion(page.id, version);
      if (epochs.current === at) dispatch({ type: "preview", snapshot });
    } catch (e) {
      reportFailure(at, e);
    }
  };

  const handleRestore = async (version: number) => {
    if (!page || busy) return;
    const at = begin("restoring");
    try {
      const restored = await restoreVersion(page.id, version, page.version);
      dispatch({ type: "restored", epoch: at, ...restored });
      say({ role: "assistant", text: restored.message });
    } catch (e) {
      reportFailure(at, e);
    } finally {
      end(at);
    }
  };

  const pending = changedFields(page?.sections ?? [], sections);
  const recoloured = recolouredKeys(draft.theme, page?.theme);
  const { renamed, rebriefed } = briefChanges(draft.brief, savedBrief);
  const unsaved =
    pending.length +
    (recoloured.length ? 1 : 0) +
    (renamed ? 1 : 0) +
    (rebriefed ? 1 : 0);

  const handleSave = async () => {
    if (!page || busy || unsaved === 0) return;
    const at = begin("saving");
    try {
      const changes: EditChange[] = [
        ...(recoloured.length && draft.theme
          ? [
              {
                action: "setTheme" as const,
                args: Object.fromEntries(
                  recoloured.map((key) => [key, draft.theme![key]]),
                ),
              },
            ]
          : []),
        ...(renamed && draft.brief
          ? [
              {
                action: "setName" as const,
                args: { value: draft.brief.business.trim() },
              },
            ]
          : []),
        ...pending.map((change) => ({
          action: "editContent" as const,
          args: {
            section: change.section,
            field: change.field,
            value: change.value,
          },
        })),
      ];

      if (changes.length) {
        await absorb(at, await applyEdits(page.id, page.version, changes));
      }
      if (draft.brief && buildId) {
        const saved = {
          ...draft.brief,
          business: draft.brief.business.trim(),
          tone: draft.brief.tone ?? null,
        };
        await saveBuild(buildId, { brief: saved, title: saved.business });
        dispatch({ type: "brief-saved", epoch: at, brief: saved });
      }
    } catch (e) {
      reportFailure(at, e);
    } finally {
      end(at);
    }
  };

  const handleUndo = () => {
    if (busy) return;
    dispatch({ type: "undo" });
  };

  const handleRename = async (wanted: string) => {
    if (!page || busy) return;
    const at = begin("renaming");
    try {
      const moved = await renamePage(page.id, wanted);
      dispatch({ type: "renamed", epoch: at, url: moved.url });
      say({ role: "assistant", text: `The page now lives at ${moved.url}.` });
      await refreshBuilds();
    } catch (e) {
      reportFailure(at, e);
    } finally {
      end(at);
    }
  };

  const handlePublish = async () => {
    if (!page || busy || unsaved > 0 || publishHold(page.readiness)) return;
    const at = begin("publishing");
    try {
      const result = await publishPage(page.id, page.version);
      dispatch({
        type: "published",
        epoch: at,
        published: { version: result.version, when: result.when },
      });
      say({
        role: "assistant",
        text: `Published v${result.version} at ${result.url}.`,
      });
    } catch (e) {
      reportFailure(at, e);
    } finally {
      end(at);
    }
  };

  useEffect(() => {
    if (busy || !buildId || messages.length === 0) return;
    const turns = messages.map(({ role, text, tone, clarification }) => ({
      role,
      text,
      tone,
      clarification: clarification ?? undefined,
    }));
    saveBuild(buildId, {
      messages: turns,
      ...(page?.name ? { title: page.name } : {}),
      ...(savedBrief
        ? { brief: { ...savedBrief, tone: savedBrief.tone ?? null }, summary }
        : {}),
    }).catch(() => {});
  }, [busy, messages, buildId, page?.name, savedBrief, summary]);

  if (isLoading) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-ui-canvas">
        <span className="h-8 w-8 animate-spin rounded-full border-2 border-ui-border border-t-ui-accent" />
      </div>
    );
  }

  if (required && !user) return <LoginScreen />;

  const hasPage = !!page && sections.length > 0;
  const pageUrl = page?.url ?? null;
  const pageName = page?.name ?? null;

  return (
    <div className="flex h-dvh flex-col bg-ui-canvas font-ui text-ui-text">
      <TopBar
        builds={builds}
        buildId={buildId}
        buildTitle={pageName ?? "New page"}
        pageUrl={pageUrl}
        pageName={pageName}
        published={published}
        busy={busy || recorder.isRecording}
        user={user}
        canSignOut={required}
        onOpenBuild={reopenBuild}
        onNewBuild={startBuild}
        onOpenMenu={refreshBuilds}
        onSignOut={logout}
        showPanelsToggle={hasPage}
        panelsOpen={panelsOpen}
        panelsMarked={!!selected}
        onTogglePanels={() => setPanelsOpen((was) => !was)}
      />

      <main
        className={`flex min-h-0 flex-1 flex-col gap-3 p-3 sm:gap-4 sm:p-4 lg:grid lg:gap-5 lg:p-5 ${
          hasPage ? "lg:grid-cols-[minmax(0,1fr)_340px]" : "lg:grid-cols-1"
        }`}
      >
        <div
          className={`min-h-0 flex-1 flex-col gap-3 sm:gap-4 lg:gap-5 ${
            hasPage && view === "panels" ? "hidden sm:flex" : "flex"
          }`}
        >
          {hasPage ? (
            <>
              <ConflictBar
                conflict={conflict}
                onRefresh={refreshPage}
                busy={busy}
              />
              <div
                className={`min-h-0 flex-1 flex-col ${
                  view === "canvas" ? "flex" : "hidden sm:flex"
                }`}
              >
              <PageCanvas
                sections={preview?.sections ?? sections}
                theme={preview ? preview.theme : draft.theme}
                pageUrl={pageUrl}
                published={published}
                live={live}
                readiness={preview ? null : page.readiness}
                onApprove={(section) =>
                  runStructuralEdit({ action: "approveSection", args: { section } })
                }
                isPublishing={isPublishing}
                isWorking={isWorking || preview !== null}
                unsaved={unsaved}
                selectedIndex={selectedIndex}
                onEdit={preview ? () => {} : editSectionField}
                selectedPath={selectedPath}
                reveal={reveal}
                onSelect={(index, element) =>
                  dispatch({ type: "select", index, path: element?.path })
                }
                onRemove={(section) =>
                  preview ||
                  runStructuralEdit({
                    action: "removeSection",
                    args: { section },
                  })
                }
                onMove={(section, position) =>
                  preview ||
                  runStructuralEdit({
                    action: "moveSection",
                    args: { section, position },
                  })
                }
                onRename={handleRename}
                onSave={handleSave}
                onUndo={handleUndo}
                onPublish={handlePublish}
              />
              </div>
            </>
          ) : (
            <EmptyState
              isRecording={recorder.isRecording}
              isWorking={isWorking}
              rejection={rejection}
              onPick={handleSend}
            />
          )}

          <div
            className={
              hasPage
                ? `min-h-0 flex-col sm:flex sm:flex-none ${
                    view === "chat" ? "flex flex-1" : "hidden"
                  }`
                : "mx-auto w-full max-w-2xl shrink-0"
            }
          >
            <Chat
              messages={messages}
              isRecording={recorder.isRecording}
              isWorking={isWorking}
              isPublishing={isPublishing}
              hasPage={hasPage}
              progress={progress}
              selectedSection={selectedType}
              models={models}
              model={model}
              onClearSection={() => dispatch({ type: "select", index: -1 })}
              onModelChange={setModel}
              onSend={handleSend}
              onMicClick={handleMicClick}
              compact={!hasPage}
            />
          </div>
        </div>

        {hasPage && panelsOpen && (
          <button
            type="button"
            tabIndex={-1}
            aria-label="Close the editing panels"
            onClick={() => setPanelsOpen(false)}
            className="fixed inset-x-0 bottom-0 top-14 z-30 hidden bg-ui-text/20 sm:block lg:hidden"
          />
        )}

        {hasPage && (
          <aside
            className={`z-40 min-h-0 flex-1 flex-col gap-3 overflow-y-auto sm:fixed sm:bottom-0 sm:right-0 sm:top-14 sm:w-[21rem] sm:max-w-[calc(100vw-2.5rem)] sm:gap-4 sm:border-l sm:border-ui-border sm:bg-ui-canvas sm:p-4 sm:shadow-[-8px_0_32px_rgba(16,24,40,0.12)] sm:transition-transform lg:static lg:w-auto lg:max-w-none lg:translate-x-0 lg:gap-5 lg:overflow-visible lg:border-l-0 lg:bg-transparent lg:p-0 lg:shadow-none ${
              view === "panels" ? "flex" : "hidden sm:flex"
            } ${
              panelsOpen
                ? "sm:visible sm:translate-x-0"
                : "sm:invisible sm:translate-x-full"
            } lg:visible`}
          >
            <PageConfig
              brief={draft.brief ?? { business: page.name ?? "", audience: "--", goal: "--" }}
              onBriefChange={(next) => dispatch({ type: "edit-brief", brief: next })}
              theme={draft.theme}
              versions={versions}
              isWorking={busy}
              onPreviewTheme={(theme) => dispatch({ type: "edit-theme", theme })}
              onCommitTheme={(colors) =>
                dispatch({
                  type: "edit-theme",
                  theme: draft.theme
                    ? ({ ...draft.theme, ...colors } as Theme)
                    : draft.theme,
                })
              }
              onRestore={handleRestore}
              previewing={preview?.version}
              onPreviewVersion={handlePreviewVersion}
            />

            <Inspector
              section={selected}
              issue={preview ? null : issueFor(page.readiness, selectedIndex)}
              onApprove={(section) =>
                runStructuralEdit({ action: "approveSection", args: { section } })
              }
              isWorking={busy || preview !== null}
              selectedPath={selectedPath}
              onSelectElement={(path) => {
                dispatch({ type: "select", index: selectedIndex, path });
                setReveal((n) => n + 1);
              }}
              onPick={(path, kind) => setPicking({ path, kind })}
              onEditPath={(path, value) =>
                runStructuralEdit({
                  action: "editContent",
                  args: { section: sections[selectedIndex].type, path, value },
                })
              }
              onRemoveItem={(path) =>
                runStructuralEdit({
                  action: "removeItem",
                  args: { section: sections[selectedIndex].type, path },
                })
              }
              onAddItem={(path) =>
                runStructuralEdit({
                  action: "addItem",
                  args: {
                    section: sections[selectedIndex].type,
                    ...(path ? { path } : {}),
                  },
                })
              }
              onMoveItem={(path, to) =>
                runStructuralEdit({
                  action: "moveItem",
                  args: {
                    section: sections[selectedIndex].type,
                    path,
                    position: String(to),
                  },
                })
              }
              onSetVariant={(variant) =>
                runStructuralEdit({
                  action: "setVariant",
                  args: { section: sections[selectedIndex].type, variant },
                })
              }
            />
          </aside>
        )}
      </main>

      {hasPage && (
        <ViewTabs
          view={view}
          marked={selected ? "panels" : null}
          onChange={setView}
        />
      )}

      {picking && sections[selectedIndex] && (
        <MediaPicker
          kind={picking.kind}
          title={`Replace ${picking.kind} -- ${SECTION_LABELS[sections[selectedIndex].type]}`}
          suggestion={
            picking.kind === "icon"
              ? ""
              : [draft.brief?.business, draft.brief?.goal].filter(Boolean).join(" ")
          }
          onClose={() => setPicking(null)}
          onChoose={(value) =>
            runStructuralEdit(
              picking.kind === "icon"
                ? {
                    action: "setIcon",
                    args: {
                      section: sections[selectedIndex].type,
                      path: picking.path,
                      icon: value,
                    },
                  }
                : {
                    action: "replaceImage",
                    args: {
                      section: sections[selectedIndex].type,
                      path: picking.path,
                      query: value,
                    },
                  },
            )
          }
        />
      )}
    </div>
  );
}
