import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  INITIAL_STATE,
  asBrief,
  briefChanges,
  hasLiveCopy,
  isPublished,
  publishHold,
  recolouredKeys,
  reduce,
  type EditorAction,
  type EditorState,
} from "./builder.ts";
import type { CommandResponse, ValidatedPage } from "./orchestrator";
import type { BuildDetail } from "./builds";

const HERO = {
  type: "hero",
  headline: "Welcome",
  image: { src: "/images/hero-section.jpg", alt: "" },
  button: { label: "Go" },
} as const;

function page(overrides: Partial<ValidatedPage> = {}): ValidatedPage {
  return {
    id: "p1",
    version: 1,
    name: "Maria's Bakery",
    url: "/maria-s-bakery",
    sections: [HERO],
    theme: null,
    published: null,
    readiness: { ready: true, blocking: [], warnings: [] },
    ...overrides,
  } as ValidatedPage;
}

function response(
  overrides: Partial<CommandResponse> = {},
): CommandResponse {
  return {
    clarification: null,
    commandId: null,
    sessionId: null,
    language: null,
    recognizedCommand: "a page for Maria's Bakery",
    message: "Done.",
    summary: "Building a landing page for Maria's Bakery.",
    brief: {
      business: "Maria's Bakery",
      audience: "families",
      goal: "orders",
      tone: null,
    },
    clarifications: [],
    versions: [
      { id: "v1", version: 1, label: "Initial draft", when: "now", published: false },
    ],
    page: page(),
    plan: { action: "createPage", schema: [], operations: [] },
    validation: { valid: true, gates: null },
    ...overrides,
  };
}

function build(overrides: Partial<BuildDetail> = {}): BuildDetail {
  return {
    id: "b1",
    title: "Maria's Bakery",
    pageId: "p1",
    turns: 0,
    messages: [],
    brief: null,
    summary: null,
    ...overrides,
  };
}

function run(...actions: EditorAction[]): EditorState {
  return actions.reduce(reduce, INITIAL_STATE);
}

describe("a confirmed command", () => {
  it("replaces the draft with the confirmed page and remembers the brief", () => {
    const state = run(
      { type: "switch-build", epoch: 1, buildId: "b1" },
      { type: "confirmed", epoch: 1, response: response() },
    );
    assert.equal(state.page?.id, "p1");
    assert.deepEqual(state.draft.sections, [HERO]);
    assert.equal(state.brief?.business, "Maria's Bakery");
    assert.equal(state.draft.brief?.business, "Maria's Bakery");
    assert.equal(state.versions.length, 1);
  });

  it("keeps the selected section when the same page comes back", () => {
    const faq = { type: "faq", items: [] } as unknown as typeof HERO;
    const first = run(
      { type: "switch-build", epoch: 1, buildId: "b1" },
      {
        type: "confirmed",
        epoch: 1,
        response: response({ page: page({ sections: [HERO, faq] }) }),
      },
      { type: "select", index: 1, path: "items" },
    );
    const again = reduce(first, {
      type: "confirmed",
      epoch: 1,
      response: response({ page: page({ version: 2, sections: [faq, HERO] }) }),
    });
    assert.equal(again.selectedIndex, 0);
    assert.equal(again.selectedPath, "items");

    const other = reduce(first, {
      type: "confirmed",
      epoch: 1,
      response: response({ page: page({ id: "p2" }) }),
    });
    assert.equal(other.selectedIndex, 0);
    assert.equal(other.selectedPath, undefined);
  });

  it("a clarification only carries the session forward", () => {
    const state = run(
      { type: "switch-build", epoch: 1, buildId: "b1" },
      {
        type: "confirmed",
        epoch: 1,
        response: response({
          page: null,
          clarification: {
            needed: true,
            question: "Who is it for?",
            missing: ["audience"],
            fields: [],
            sessionId: "s9",
            intent: "createPage",
            asked: 1,
            limit: 2,
          },
        }),
      },
    );
    assert.equal(state.sessionId, "s9");
    assert.equal(state.page, null);
    assert.deepEqual(state.draft.sections, []);
  });
});

describe("local edits, save and undo", () => {
  const saved = run(
    { type: "switch-build", epoch: 1, buildId: "b1" },
    { type: "confirmed", epoch: 1, response: response() },
  );

  it("editing changes only the draft", () => {
    const edited = reduce(saved, {
      type: "edit-sections",
      sections: [{ ...HERO, headline: "Fresh bread" }],
    });
    assert.equal(edited.page?.sections[0], HERO);
    assert.equal((edited.draft.sections[0] as typeof HERO).headline, "Fresh bread");
  });

  it("undo returns the draft to the confirmed page and brief", () => {
    const edited = run(
      { type: "switch-build", epoch: 1, buildId: "b1" },
      { type: "confirmed", epoch: 1, response: response() },
      { type: "edit-sections", sections: [{ ...HERO, headline: "Fresh bread" }] },
      { type: "edit-brief", brief: { business: "Other", audience: "x", goal: "y" } },
      { type: "undo" },
    );
    assert.deepEqual(edited.draft.sections, [HERO]);
    assert.equal(edited.draft.brief?.business, "Maria's Bakery");
  });

  it("a save is a confirmed response at the next version", () => {
    const state = reduce(saved, {
      type: "confirmed",
      epoch: 1,
      response: response({ page: page({ version: 2 }) }),
    });
    assert.equal(state.page?.version, 2);
    assert.equal(state.conflict, null);
  });

  it("an edit on the same page keeps the build's brief and any unsaved brief edits", () => {
    const editing = reduce(saved, {
      type: "edit-brief",
      brief: { business: "Maria's Bakery", audience: "students", goal: "orders" },
    });
    const state = reduce(editing, {
      type: "confirmed",
      epoch: 1,
      response: response({
        page: page({ version: 2 }),
        brief: { business: "Maria's Bakery", audience: "Local customers",
                 goal: "Generate enquiries", tone: null },
      }),
    });
    assert.equal(state.brief?.audience, "families");
    assert.equal(state.draft.brief?.audience, "students");
  });

  it("a rename on the same page updates the business in both briefs", () => {
    const state = reduce(saved, {
      type: "confirmed",
      epoch: 1,
      response: response({ page: page({ version: 2, name: "Maria's Bakery Co" }) }),
    });
    assert.equal(state.brief?.business, "Maria's Bakery Co");
    assert.equal(state.draft.brief?.business, "Maria's Bakery Co");
    assert.equal(state.brief?.audience, "families");
  });

  it("brief changes are derived from draft versus confirmed", () => {
    assert.deepEqual(
      briefChanges(
        { business: "Maria's Bakery ", audience: "families", goal: "orders" },
        saved.brief,
      ),
      { renamed: false, rebriefed: false },
    );
    assert.deepEqual(
      briefChanges(
        { business: "New", audience: "families", goal: "walk-ins" },
        saved.brief,
      ),
      { renamed: true, rebriefed: true },
    );
  });

  it("recoloured keys compare the draft theme with the confirmed one", () => {
    const theme = { primary: "#111", accent: "#222", background: "#fff" };
    assert.deepEqual(
      recolouredKeys({ ...theme, primary: "#000" } as never, theme as never),
      ["primary"],
    );
    assert.deepEqual(recolouredKeys(null, theme as never), []);
  });
});

describe("publication status", () => {
  it("is derived from the confirmed and published versions", () => {
    assert.equal(isPublished(null), false);
    assert.equal(isPublished(page()), false);
    assert.equal(isPublished(page({ published: { version: 1, when: "t" } })), true);
    assert.equal(
      isPublished(page({ version: 3, published: { version: 2, when: "t" } })),
      false,
    );
    assert.equal(hasLiveCopy(page({ version: 3, published: { version: 2, when: "t" } })), true);
  });

  it("publishing marks the confirmed version and the matching history entry", () => {
    const state = run(
      { type: "switch-build", epoch: 1, buildId: "b1" },
      { type: "confirmed", epoch: 1, response: response() },
      { type: "published", epoch: 1, published: { version: 1, when: "t" } },
    );
    assert.equal(isPublished(state.page), true);
    assert.deepEqual(state.versions.map((v) => v.published), [true]);

    const edited = reduce(state, {
      type: "confirmed",
      epoch: 1,
      response: response({
        page: page({ version: 2, published: { version: 1, when: "t" } }),
        versions: [
          { id: "v2", version: 2, label: "Edit", when: "t", published: false },
          { id: "v1", version: 1, label: "Initial draft", when: "t", published: true },
        ],
      }),
    });
    assert.equal(isPublished(edited.page), false);
    assert.equal(hasLiveCopy(edited.page), true);
  });

  it("holds publishing until placeholders are replaced and reviews approved", () => {
    const placeholder = {
      section: "faq",
      index: 1,
      provenance: "placeholder",
      reason: "Placeholder text",
    };
    const warning = {
      section: "testimonials",
      index: 2,
      provenance: "generated",
      reason: "Sample reviews, not real ones",
    };

    assert.equal(publishHold(null), null);
    assert.equal(publishHold({ ready: true, blocking: [], warnings: [] }), null);
    assert.equal(
      publishHold({ ready: true, blocking: [], warnings: [warning] }),
      "review",
    );
    assert.equal(
      publishHold({ ready: false, blocking: [placeholder], warnings: [warning] }),
      "placeholder",
    );
  });
});

describe("restore", () => {
  it("makes the restored page the confirmed draft without touching the published reference", () => {
    const state = run(
      { type: "switch-build", epoch: 1, buildId: "b1" },
      { type: "confirmed", epoch: 1, response: response() },
      { type: "published", epoch: 1, published: { version: 1, when: "t" } },
      { type: "preview", snapshot: { version: 1, label: "x", when: "t", sections: [] } },
      {
        type: "restored",
        epoch: 1,
        page: page({ version: 3, published: { version: 1, when: "t" } }),
        versions: [],
      },
    );
    assert.equal(state.page?.version, 3);
    assert.equal(state.page?.published?.version, 1);
    assert.equal(state.preview, null);
    assert.deepEqual(state.draft.sections, [HERO]);
  });
});

describe("switching builds", () => {
  it("resets the workspace and ignores responses from the previous build", () => {
    const first = run(
      { type: "switch-build", epoch: 1, buildId: "b1" },
      { type: "begin", epoch: 1, phase: "running" },
    );
    const switched = reduce(first, { type: "switch-build", epoch: 2, buildId: "b2" });
    assert.equal(switched.epoch, 2);
    assert.equal(reduce(switched, { type: "switch-build", epoch: 1, buildId: "b0" }), switched);
    assert.equal(switched.phase, "idle");
    assert.equal(switched.page, null);

    const late = reduce(switched, {
      type: "confirmed",
      epoch: 1,
      response: response(),
    });
    assert.equal(late.page, null);
    assert.deepEqual(late.draft.sections, []);

    const lateEnd = reduce(
      reduce(switched, { type: "begin", epoch: 2, phase: "saving" }),
      { type: "end", epoch: 1 },
    );
    assert.equal(lateEnd.phase, "saving");
  });

  it("reopening restores the build's page, brief and conversation", () => {
    const state = run(
      { type: "switch-build", epoch: 1, buildId: "b1" },
      {
        type: "reopened",
        epoch: 1,
        build: build({
          messages: [{ role: "user", text: "hi" }],
          brief: {
            business: "Maria's Bakery",
            audience: "families",
            goal: "orders",
            tone: null,
          },
          summary: "Editing Maria's Bakery.",
        }),
        page: page({ version: 2, published: { version: 2, when: "t" } }),
        versions: [{ id: "v2", version: 2, label: "Edit", when: "t", published: true }],
      },
    );
    assert.equal(state.messages.length, 1);
    assert.equal(state.nextMessageId, 1);
    assert.equal(isPublished(state.page), true);
    assert.equal(state.draft.brief?.audience, "families");
    assert.equal(state.summary, "Editing Maria's Bakery.");
  });

  it("a reopen from a previous epoch is dropped", () => {
    const state = run(
      { type: "switch-build", epoch: 1, buildId: "b1" },
      { type: "switch-build", epoch: 2, buildId: "b2" },
      { type: "reopened", epoch: 1, build: build(), page: page(), versions: [] },
    );
    assert.equal(state.page, null);
    assert.equal(state.buildId, "b2");
  });
});

describe("conflicts and rejections", () => {
  it("a conflict is kept until the next confirmed response", () => {
    const state = run(
      { type: "switch-build", epoch: 1, buildId: "b1" },
      { type: "confirmed", epoch: 1, response: response() },
      { type: "edit-sections", sections: [{ ...HERO, headline: "Mine" }] },
      { type: "conflict", epoch: 1, conflict: { expected: 1, current: 2 } },
    );
    assert.deepEqual(state.conflict, { expected: 1, current: 2 });
    assert.equal((state.draft.sections[0] as typeof HERO).headline, "Mine");

    const refreshed = reduce(state, {
      type: "confirmed",
      epoch: 1,
      response: response({ page: page({ version: 2 }) }),
    });
    assert.equal(refreshed.conflict, null);
  });

  it("beginning new work clears the last rejection", () => {
    const state = run(
      { type: "switch-build", epoch: 1, buildId: "b1" },
      { type: "rejected", epoch: 1, rejection: { stage: "intent", message: "no" } },
      { type: "begin", epoch: 1, phase: "running" },
    );
    assert.equal(state.rejection, null);
  });
});

describe("asBrief", () => {
  it("fills gaps and falls back to the page name", () => {
    assert.equal(asBrief(null), null);
    assert.deepEqual(asBrief(null, "Maria's Bakery"), {
      business: "Maria's Bakery",
      audience: "--",
      goal: "--",
      tone: null,
    });
    assert.equal(
      asBrief({ business: "X", audience: null, goal: null, tone: null })?.audience,
      "--",
    );
  });
});

describe("refreshing after a conflict", () => {
  it("adopts the server page but keeps the local draft", () => {
    const state = run(
      { type: "switch-build", epoch: 1, buildId: "b1" },
      { type: "confirmed", epoch: 1, response: response() },
      { type: "edit-sections", sections: [{ ...HERO, headline: "Mine" }] },
      { type: "conflict", epoch: 1, conflict: { expected: 1, current: 2 } },
      { type: "refreshed", epoch: 1, page: page({ version: 2 }), versions: [] },
    );
    assert.equal(state.page?.version, 2);
    assert.equal(state.conflict, null);
    assert.equal((state.draft.sections[0] as typeof HERO).headline, "Mine");
  });
});
